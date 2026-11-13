# Rebuilds the Vanna knowledge base from scratch (schema + business docs + Q-SQL pairs).
# The app also does this automatically on first start; run this after editing
# training/knowledge.py:   python training/train.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.vanna_setup import vn, train_all


def main():
    existing = vn.get_training_data()
    print(f"Removing {len(existing)} existing training items...")
    for item_id in existing["id"]:
        vn.remove_training_data(id=item_id)

    print("Training...")
    train_all(vn)
    print(f"Done. {len(vn.get_training_data())} items in the vector store.")


if __name__ == "__main__":
    main()
