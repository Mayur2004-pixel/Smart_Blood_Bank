import csv
import io
import json
import os
from datetime import datetime, date

from flask import (Flask, render_template, request, redirect, url_for, flash,
                   jsonify, Response)

from algorithms import (
    blood_compatible, dijkstra, DonorBST, EmergencyPriorityQueue,
    sort_donors_by_distance, COMPATIBILITY, bfs_path, path_length, floyd_warshall,
    prim_mst, benchmark_sorts, binary_search_by_name, merge_sort, is_eligible,
    days_since, next_eligible_date, greedy_allocate, allocation_order,
    knapsack_camp, DONATION_GAP_DAYS,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DONOR_FILE = os.path.join(DATA_DIR, "donors.json")
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.json")
REQUEST_FILE = os.path.join(DATA_DIR, "requests.json")
ACTIVITY_FILE = os.path.join(DATA_DIR, "activity.json")

BLOOD_GROUPS = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
LOW_STOCK = 3  # units; at or below this a group is flagged "low"

app = Flask(__name__)
app.secret_key = "change-this-demo-secret-key"


# ----------------------------------------------------------------- storage
def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_donors():
    return _load(DONOR_FILE, [])


def save_donors(d):
    _save(DONOR_FILE, d)


def load_inventory():
    inv = _load(INVENTORY_FILE, {})
    return {g: int(inv.get(g, 0)) for g in BLOOD_GROUPS}


def save_inventory(i):
    _save(INVENTORY_FILE, i)


def load_requests():
    return _load(REQUEST_FILE, [])


def save_requests(r):
    _save(REQUEST_FILE, r)


def log_activity(text):
    log = _load(ACTIVITY_FILE, [])
    log.insert(0, {"time": datetime.now().strftime("%d %b %H:%M"), "text": text})
    _save(ACTIVITY_FILE, log[:30])


# Example road network: locations are vertices and roads are weighted edges (km).
ROAD_GRAPH = {
    "City Hospital": {"Model Town": 3, "Civil Lines": 5, "Bus Stand": 4},
    "Model Town": {"City Hospital": 3, "University": 4, "Bus Stand": 2},
    "Civil Lines": {"City Hospital": 5, "University": 3, "Railway Station": 4},
    "Bus Stand": {"City Hospital": 4, "Model Town": 2, "Railway Station": 3},
    "University": {"Model Town": 4, "Civil Lines": 3, "Railway Station": 2},
    "Railway Station": {"Bus Stand": 3, "Civil Lines": 4, "University": 2},
}
# Fixed SVG coordinates for the network map page.
NODE_POS = {
    "City Hospital": (90, 150), "Model Town": (250, 60), "Civil Lines": (250, 250),
    "Bus Stand": (260, 155), "University": (450, 100), "Railway Station": (450, 220),
}


def build_tree(donors):
    tree = DonorBST()
    for d in donors:
        tree.insert(d)
    return tree


def get_matches(blood_group, hospital, only_eligible=True):
    donors = load_donors()
    tree = build_tree(donors)
    ranked = []
    for donor in tree.inorder():
        if not blood_compatible(donor["blood_group"], blood_group):
            continue
        ok = is_eligible(donor) if only_eligible else donor["available"]
        if not ok:
            continue
        distance, path = dijkstra(ROAD_GRAPH, hospital, donor["location"])
        if distance is not None:
            item = dict(donor)
            item["distance"] = distance
            item["route"] = path
            item["exact"] = donor["blood_group"] == blood_group
            ranked.append(item)
    return sort_donors_by_distance(ranked)


def enrich(donor):
    d = dict(donor)
    d["eligible"] = is_eligible(donor)
    d["days_since"] = days_since(donor.get("last_donation"))
    d["next_date"] = next_eligible_date(donor)
    return d


# ---------------------------------------------------------------- dashboard
@app.route("/")
def index():
    donors = load_donors()
    inv = load_inventory()
    reqs = load_requests()
    available = sum(1 for d in donors if is_eligible(d))
    low = [g for g, u in inv.items() if u <= LOW_STOCK]
    pending = [r for r in reqs if r["status"] == "pending"]
    return render_template(
        "index.html", donors=donors, available=available, inventory=inv,
        total_units=sum(inv.values()), low=low, low_threshold=LOW_STOCK,
        pending=len(pending), activity=_load(ACTIVITY_FILE, [])[:8],
        max_units=max(max(inv.values()), 1))


# ------------------------------------------------------------------- search
@app.route("/search", methods=["GET", "POST"])
def search():
    matches, blood_group, hospital, only_eligible = [], "O+", "City Hospital", True
    searched = False
    if request.method == "POST":
        searched = True
        blood_group = request.form.get("blood_group", "O+")
        hospital = request.form.get("hospital", "City Hospital")
        only_eligible = request.form.get("only_eligible") == "on"
        if blood_group not in COMPATIBILITY or hospital not in ROAD_GRAPH:
            flash("Invalid blood group or location.", "danger")
        else:
            matches = [enrich(m) | {"distance": m["distance"], "route": m["route"],
                                    "exact": m["exact"]}
                       for m in get_matches(blood_group, hospital, only_eligible)]
            if not matches:
                flash("No eligible compatible donors were found in the sample dataset.", "warning")
    inv = load_inventory()
    stock_plan = None
    if searched and blood_group in COMPATIBILITY:
        stock_plan = [(g, inv[g]) for g in allocation_order(blood_group)]
    return render_template("search.html", matches=matches, blood_group=blood_group,
                           hospital=hospital, only_eligible=only_eligible,
                           locations=sorted(ROAD_GRAPH), groups=BLOOD_GROUPS,
                           stock_plan=stock_plan)


# ------------------------------------------------------------------- donors
@app.route("/donors", methods=["GET", "POST"])
def donors_page():
    donors = load_donors()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        bg = request.form.get("blood_group")
        loc = request.form.get("location")
        if not name or not phone:
            flash("Please enter donor name and contact number.", "danger")
        elif bg not in COMPATIBILITY or loc not in ROAD_GRAPH:
            flash("Invalid blood group or location.", "danger")
        elif not phone.isdigit() or len(phone) != 10:
            flash("Phone must be 10 digits (demo number).", "danger")
        else:
            donors.append({
                "id": max([d["id"] for d in donors], default=0) + 1,
                "name": name, "blood_group": bg, "location": loc, "phone": phone,
                "available": True, "last_donation": None, "total_donations": 0})
            save_donors(donors)
            log_activity(f"Donor added: {name} ({bg})")
            flash("Demo donor added successfully.", "success")
            return redirect(url_for("donors_page"))

    q = request.args.get("q", "").strip()
    fgroup = request.args.get("group", "")
    status = request.args.get("status", "")
    sort = request.args.get("sort", "id")

    rows = [enrich(d) for d in donors]
    if q:
        # Binary search on a name-sorted list (prefix match), plus substring fallback.
        by_name = merge_sort(rows, key=lambda d: d["name"].lower())
        hits = {d["id"] for d in binary_search_by_name(by_name, q)}
        hits |= {d["id"] for d in rows if q.lower() in d["name"].lower()
                 or q in d["phone"] or q.lower() == d["location"].lower()}
        rows = [d for d in rows if d["id"] in hits]
    if fgroup:
        rows = [d for d in rows if d["blood_group"] == fgroup]
    if status == "eligible":
        rows = [d for d in rows if d["eligible"]]
    elif status == "unavailable":
        rows = [d for d in rows if not d["available"]]
    elif status == "resting":
        rows = [d for d in rows if d["available"] and not d["eligible"]]
    keys = {"id": lambda d: d["id"], "name": lambda d: d["name"].lower(),
            "group": lambda d: d["blood_group"], "donations": lambda d: -d.get("total_donations", 0)}
    rows = merge_sort(rows, key=keys.get(sort, keys["id"]))
    return render_template("donors.html", donors=rows, locations=sorted(ROAD_GRAPH),
                           groups=BLOOD_GROUPS, q=q, fgroup=fgroup, status=status,
                           sort=sort, gap=DONATION_GAP_DAYS, total=len(donors))


@app.route("/donor/<int:donor_id>/toggle", methods=["POST"])
def toggle_donor(donor_id):
    donors = load_donors()
    for donor in donors:
        if donor["id"] == donor_id:
            donor["available"] = not donor["available"]
            break
    save_donors(donors)
    flash("Donor availability updated.", "success")
    return redirect(request.referrer or url_for("donors_page"))


@app.route("/donor/<int:donor_id>/delete", methods=["POST"])
def delete_donor(donor_id):
    donors = load_donors()
    gone = [d for d in donors if d["id"] == donor_id]
    save_donors([d for d in donors if d["id"] != donor_id])
    if gone:
        log_activity(f"Donor removed: {gone[0]['name']}")
        flash("Donor removed.", "success")
    return redirect(url_for("donors_page"))


@app.route("/donor/<int:donor_id>/donate", methods=["POST"])
def record_donation(donor_id):
    donors = load_donors()
    for d in donors:
        if d["id"] == donor_id:
            if not is_eligible(d):
                flash(f"{d['name']} is not eligible to donate yet "
                      f"(next eligible: {next_eligible_date(d) or 'n/a'}).", "warning")
                return redirect(url_for("donors_page"))
            d["last_donation"] = date.today().isoformat()
            d["total_donations"] = d.get("total_donations", 0) + 1
            inv = load_inventory()
            inv[d["blood_group"]] += 1
            save_inventory(inv)
            save_donors(donors)
            log_activity(f"Donation recorded: {d['name']} (+1 unit {d['blood_group']})")
            flash(f"Donation recorded. +1 unit of {d['blood_group']} added to inventory.", "success")
            break
    return redirect(url_for("donors_page"))


@app.route("/donors/lookup")
def lookup():
    """Find a donor by ID using the BST and report how many comparisons it took."""
    result, steps, height, donor_id = None, None, None, request.args.get("id", "")
    donors = load_donors()
    tree = build_tree(donors)
    height = tree.height()
    if donor_id.isdigit():
        result, steps = tree.search(int(donor_id))
        if result is None:
            flash(f"No donor with ID {donor_id}.", "warning")
    return render_template("lookup.html", donor=enrich(result) if result else None,
                           steps=steps, height=height, n=len(donors), donor_id=donor_id)


@app.route("/donors/export.csv")
def export_csv():
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["id", "name", "blood_group", "location", "phone", "available",
                "last_donation", "total_donations"])
    for d in load_donors():
        w.writerow([d["id"], d["name"], d["blood_group"], d["location"], d["phone"],
                    d["available"], d.get("last_donation") or "", d.get("total_donations", 0)])
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=donors.csv"})


# ---------------------------------------------------------------- inventory
@app.route("/inventory", methods=["GET", "POST"])
def inventory():
    inv = load_inventory()
    if request.method == "POST":
        g = request.form.get("blood_group")
        try:
            delta = int(request.form.get("delta", "0"))
        except ValueError:
            delta = 0
        if g not in inv or delta == 0:
            flash("Choose a blood group and a non-zero number of units.", "danger")
        elif inv[g] + delta < 0:
            flash(f"Only {inv[g]} unit(s) of {g} in stock.", "danger")
        else:
            inv[g] += delta
            save_inventory(inv)
            log_activity(f"Inventory {g}: {'+' if delta > 0 else ''}{delta} unit(s)")
            flash("Inventory updated.", "success")
        return redirect(url_for("inventory"))
    # How many recipient groups each donor group can serve (compatibility graph degree).
    serves = {g: [r for r in BLOOD_GROUPS if blood_compatible(g, r)] for g in BLOOD_GROUPS}
    return render_template("inventory.html", inventory=inv, groups=BLOOD_GROUPS,
                           low=LOW_STOCK, serves=serves, max_units=max(max(inv.values()), 1))


# ---------------------------------------------------------------- emergency
def _heap_from(reqs):
    q = EmergencyPriorityQueue()
    for r in reqs:
        if r["status"] == "pending":
            q.push(r)
    return q


@app.route("/emergency", methods=["GET", "POST"])
def emergency():
    reqs = load_requests()
    if request.method == "POST":
        try:
            units = int(request.form["units"])
            urgency = int(request.form["urgency"])
        except (KeyError, ValueError):
            flash("Units and urgency must be numbers.", "danger")
            return redirect(url_for("emergency"))
        patient = request.form.get("patient", "").strip()
        bg = request.form.get("blood_group")
        hospital = request.form.get("hospital", "City Hospital")
        if not patient or bg not in COMPATIBILITY or not (1 <= urgency <= 5) \
                or not (1 <= units <= 10) or hospital not in ROAD_GRAPH:
            flash("Please fill the form correctly.", "danger")
            return redirect(url_for("emergency"))
        reqs.append({"id": max([r["id"] for r in reqs], default=0) + 1, "patient": patient,
                     "blood_group": bg, "units": units, "urgency": urgency,
                     "hospital": hospital, "created": datetime.now().strftime("%d %b %H:%M:%S"),
                     "status": "pending", "allocation": []})
        save_requests(reqs)
        log_activity(f"Emergency queued: {patient} needs {units}u {bg} (urgency {urgency})")
        flash(f"Request queued for {patient} (priority {urgency}/5).", "success")
        return redirect(url_for("emergency"))

    pq = _heap_from(reqs)
    order = []
    while True:
        r = pq.pop()
        if r is None:
            break
        order.append(r)
    done = [r for r in reqs if r["status"] != "pending"][::-1]
    return render_template("emergency.html", queue=order, done=done, groups=BLOOD_GROUPS,
                           locations=sorted(ROAD_GRAPH))


@app.route("/emergency/process", methods=["POST"])
def process_next():
    reqs = load_requests()
    r = _heap_from(reqs).pop()          # highest urgency, FIFO among ties
    if r is None:
        flash("Queue is empty.", "info")
        return redirect(url_for("emergency"))
    inv = load_inventory()
    plan, short = greedy_allocate(inv, r["blood_group"], r["units"])
    for g, n in plan:
        inv[g] -= n
    save_inventory(inv)
    for x in reqs:
        if x["id"] == r["id"]:
            x["allocation"] = plan
            x["shortfall"] = short
            x["status"] = "fulfilled" if short == 0 else ("partial" if plan else "unfulfilled")
            if short:
                near = get_matches(r["blood_group"], r["hospital"])[:3]
                x["donor_suggestions"] = [f"{m['name']} ({m['blood_group']}, {m['distance']} km)" for m in near]
            x["processed"] = datetime.now().strftime("%d %b %H:%M:%S")
            final = x
    save_requests(reqs)
    txt = ", ".join(f"{n}u {g}" for g, n in plan) or "no stock"
    log_activity(f"Processed {r['patient']}: {txt}" + (f" (short {short}u)" if short else ""))
    flash(f"Processed {r['patient']}: allocated {txt}."
          + (f" Shortfall of {short} unit(s) - nearest donors suggested." if short else ""),
          "success" if not short else "warning")
    return redirect(url_for("emergency"))


@app.route("/emergency/clear", methods=["POST"])
def clear_history():
    save_requests([r for r in load_requests() if r["status"] == "pending"])
    flash("Processed history cleared.", "success")
    return redirect(url_for("emergency"))


# ---------------------------------------------------------- road network
@app.route("/network")
def network():
    nodes = sorted(ROAD_GRAPH)
    src = request.args.get("src", "City Hospital")
    dst = request.args.get("dst", "Railway Station")
    route = None
    if src in ROAD_GRAPH and dst in ROAD_GRAPH:
        dk, dpath = dijkstra(ROAD_GRAPH, src, dst)
        bh, bpath = bfs_path(ROAD_GRAPH, src, dst)
        route = {"dijkstra_km": dk, "dijkstra_path": dpath, "bfs_hops": bh,
                 "bfs_path": bpath, "bfs_km": path_length(ROAD_GRAPH, bpath) if bpath else None}
    fw_nodes, matrix = floyd_warshall(ROAD_GRAPH)
    mst_edges, mst_total = prim_mst(ROAD_GRAPH)
    all_edges = {tuple(sorted((a, b))): w for a in ROAD_GRAPH for b, w in ROAD_GRAPH[a].items()}
    mst_set = {tuple(sorted((a, b))) for a, b, _ in mst_edges}
    highlight = set()
    if route and route["dijkstra_path"]:
        p = route["dijkstra_path"]
        highlight = {tuple(sorted(x)) for x in zip(p, p[1:])}
    return render_template("network.html", nodes=nodes, src=src, dst=dst, route=route,
                           fw_nodes=fw_nodes, matrix=matrix, mst=mst_edges, mst_total=mst_total,
                           total_edges=sum(all_edges.values()), edges=all_edges, mst_set=mst_set,
                           highlight=highlight, pos=NODE_POS)


# ---------------------------------------------------------- analysis & misc
@app.route("/analysis")
def analysis():
    bench = benchmark_sorts()
    return render_template("analysis.html", bench=bench, bench_json=json.dumps(bench))


@app.route("/compatibility")
def compatibility():
    matrix = [[blood_compatible(d, r) for r in BLOOD_GROUPS] for d in BLOOD_GROUPS]
    return render_template("compatibility.html", groups=BLOOD_GROUPS, matrix=matrix)


@app.route("/camp", methods=["GET", "POST"])
def camp():
    """Donation camp planner solved with 0/1 knapsack dynamic programming."""
    budget = 10
    result = None
    inv = load_inventory()
    # Donors in groups that are low on stock and eligible are the candidates.
    cands = []
    for d in load_donors():
        if is_eligible(d):
            need = max(0, LOW_STOCK + 3 - inv[d["blood_group"]])   # value = shortage it fills
            if need:
                cands.append({"name": d["name"], "blood_group": d["blood_group"],
                              "cost": 1 + len(ROAD_GRAPH[d["location"]]) // 2,  # travel/outreach effort
                              "value": need})
    if request.method == "POST":
        try:
            budget = max(1, min(30, int(request.form.get("budget", 10))))
        except ValueError:
            budget = 10
    best, chosen = knapsack_camp(cands, budget)
    return render_template("camp.html", budget=budget, best=best, chosen=chosen,
                           cands=cands, spent=sum(c["cost"] for c in chosen))


@app.route("/api/donors")
def api_donors():
    group = request.args.get("group")
    donors = [enrich(d) for d in load_donors() if not group or d["blood_group"] == group]
    return jsonify(donors)


@app.route("/api/match")
def api_match():
    bg = request.args.get("group", "O+")
    hospital = request.args.get("hospital", "City Hospital")
    if bg not in COMPATIBILITY or hospital not in ROAD_GRAPH:
        return jsonify({"error": "invalid group or hospital"}), 400
    return jsonify(get_matches(bg, hospital))


@app.route("/api/inventory")
def api_inventory():
    return jsonify(load_inventory())


if __name__ == "__main__":
    app.run(debug=True)
