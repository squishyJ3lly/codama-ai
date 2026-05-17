from main_pipeline import process

def chat():
    print("CODAMA READY.")
    print("Type 'exit' to quit.")

    history = []

    while True:
        try:
            user = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user:
            continue

        if user.lower() in {"exit", "quit"}:
            break

        try:
            process(user, history)
        except Exception as e:
            print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    chat()