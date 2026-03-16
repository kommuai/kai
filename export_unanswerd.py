import csv
from session_state import get_unanswered

def export_to_csv(filename="unanswered.csv", limit=200):
    rows = get_unanswered(limit)
    if not rows:
        print("No unanswered questions found.")
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "User ID", "Question", "Created At"])
        for r in rows:
            writer.writerow(r)
    print(f"Exported {len(rows)} unanswered questions → {filename}")

if __name__ == "__main__":
    export_to_csv()
