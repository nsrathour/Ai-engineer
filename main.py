from app.orchestrator import run_agent


def main():
    requirement = input("What do you want to build?\n> ")

    result = run_agent(requirement)

    print("\nFINAL RESULT:")
    print(result)


if __name__ == "__main__":
    main()