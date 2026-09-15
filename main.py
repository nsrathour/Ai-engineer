from app.orchestrator import run_agent


def main():
    requirement = input("What do you want to build?\n> ")

    run_agent(requirement)


if __name__ == "__main__":
    main()