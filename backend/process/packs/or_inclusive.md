# Inclusive OR gateway (sample)

Demonstrates an **inclusive gateway** (OR-split / OR-join) after a flags user task.

Complete **Choose branches** with form data:

- `need_legal: true` and/or `need_tech: true` → corresponding review tasks (both if both true).
- At least one condition should be true (no default flow in this sample).

After taken branches finish, the join waits for them, then **Finalize** → End.

Same ScriptEngine expression dialect as the XOR pack (`approved == True`).
Not a compliance pack — training diagram for Inclusive Gateway.
