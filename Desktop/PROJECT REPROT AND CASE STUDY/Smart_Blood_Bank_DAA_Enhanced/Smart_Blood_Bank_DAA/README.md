# Smart Blood Bank and Donor Matching System (DAA Mini Project)

A Python + Flask academic demonstration of Design and Analysis of Algorithms concepts.

## Features

**Original**
- Donor record management, red-cell compatibility filtering
- Dijkstra nearest-donor ranking, BST donor index, Merge Sort ranking
- Emergency priority queue, Bootstrap web interface

**New in this version**
- **Blood inventory** - units per group, low-stock alerts, manual adjustment, dashboard stock bars
- **Persistent emergency queue** - requests saved to disk; "Process next" pops the highest urgency (FIFO on ties) and allocates stock with a **greedy** strategy (exact match first, O- conserved); shortfalls suggest nearest donors
- **Donor eligibility** - 90-day rule, last-donation date, donation counter, "Record donation" adds a unit to stock
- **Donor search / filter / sort** - name prefix search via **binary search**, filter by group & status, sort via merge sort, delete donors, CSV export
- **BST ID lookup** - shows tree height and number of comparisons used
- **Road network page** - SVG map, **Dijkstra vs BFS** route comparison, **Floyd-Warshall** all-pairs matrix, **Prim MST**
- **Donation camp planner** - **0/1 knapsack DP** picks donors to invite under a budget
- **Analysis page** - live Merge / Quick / Bubble / built-in sort benchmark chart + complexity table
- **Compatibility matrix** page and JSON API (`/api/donors`, `/api/match`, `/api/inventory`)
- Input validation (phone, units, urgency, group, location)

## DAA concepts and complexity

| Component | Algorithm / Data Structure | Expected complexity |
|---|---|---|
| Donor indexing / ID lookup | BST insert/search | Average O(log n), worst O(n) |
| Donor listing | BST inorder traversal | O(n) |
| Name search | Binary search on sorted list | O(log n + k) |
| Route (km) | Dijkstra with binary heap | O((V + E) log V) |
| Route (hops) | BFS | O(V + E) |
| All-pairs distances | Floyd-Warshall (DP) | O(V^3) |
| Cheapest connected roads | Prim MST | O(E log V) |
| Donor ranking | Merge Sort | O(n log n) |
| Benchmark | Quick Sort / Bubble Sort | avg O(n log n) / O(n^2) |
| Emergency priority | Binary heap priority queue | Push/pop O(log n) |
| Stock allocation | Greedy | O(g log g), g = 8 groups |
| Camp planner | 0/1 Knapsack DP | O(n * W) |
| Compatibility | Lookup table | O(1) |

## Requirements
- Python 3.9 or later
- pip

## Run on Windows
1. Extract the ZIP file.
2. Open the extracted `Smart_Blood_Bank_DAA` folder.
3. Click the address bar in File Explorer, type `cmd`, and press Enter.
4. Run:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

5. Open `http://127.0.0.1:5000` in your browser.

If `python` is not recognized, try `py` instead:
```bash
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
```

## Project structure

```text
Smart_Blood_Bank_DAA/
├── app.py
├── algorithms.py
├── requirements.txt
├── README.md
├── data/            donors.json, inventory.json, requests.json (activity.json is created at runtime)
├── templates/       base, index, search, donors, lookup, inventory, emergency,
│                    network, camp, analysis, compatibility
└── static/style.css
```

## Demonstrating the project
1. Open **Find Donor**.
2. Select a recipient blood group and starting hospital.
3. The app filters compatible available donors and calculates shortest road routes.
4. Results are ranked by distance using Merge Sort.
5. Open **Donors** to add a fictional donor or toggle availability.
6. Open **Emergency**, add several requests with different urgency, press **Process next** and watch the heap order and greedy stock allocation.
7. Open **Road Network**, **Camp Planner** and **Analysis** to show Floyd-Warshall, Prim, knapsack and the sorting benchmark.

## Important academic and safety limitations
- All names, phone numbers and distances are fictional sample data.
- This is not a real blood bank, donor registry, emergency dispatch or medical decision system.
- Blood compatibility here demonstrates simplified red-cell ABO/Rh matching only. Real transfusion decisions require professional testing, crossmatching, donor screening and blood-bank approval.
- Replace the sample graph and data only for a supervised academic demonstration. Do not enter real patient or donor personal information into this demo.

## Suggested viva questions
1. Why is Dijkstra suitable for finding the shortest road route?
2. What is the difference between a BST and an AVL tree?
3. Why is Merge Sort O(n log n)?
4. How does a priority queue differ from a normal queue?
5. What are the time complexities of Dijkstra, Merge Sort and BST traversal?
6. What assumptions are made by the blood compatibility table?
7. Why is BFS not correct for weighted shortest paths?
8. Compare Dijkstra and Floyd-Warshall. When is each better?
9. Why is the greedy allocation safe here, and when would greedy fail?
10. How does the knapsack DP table work and why is it O(n*W)?
