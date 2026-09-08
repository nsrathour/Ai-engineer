from agent import create_plan

requirement = input("What do you want to build?\n>")

plan = create_plan(requirement)


print(plan.risks)