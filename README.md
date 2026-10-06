# Loan Approval Multi-Agent + Docker Sandbox POC

This POC demonstrates a two-agent loan approval workflow with **memory and state management**.

## Agents

1. **CIBIL Agent** - assesses the customer's credit profile.
2. **Loan Decision Agent** - evaluates affordability and asks a Docker sandbox to calculate EMI.

The Docker sandbox is **not an agent**. It is an isolated execution environment used only for calculation.

## Memory and state architecture

```text
                    Streamlit UI
                         |
                  session_state
                  (UI/session state)
                         |
                         v
                 LangGraph Workflow
                         |
                  +------+------+
                  |             |
             Current State   Customer Memory
             LoanState       SQLite DB
                  |             |
                  v             v
              CIBIL Agent   load_memory
                  |
              Loan Decision
                  |
             Docker Sandbox
                  |
             Persist Memory
                  |
                  v
                Result
```

### State

`LoanState` carries the current workflow information:

- customer
- CIBIL result
- loan result
- EMI
- decision/reason
- loaded customer memory
- workflow ID
- number of previous assessments

This state exists for the current graph execution.

### Short-term/session state

Streamlit `st.session_state` keeps the current workflow ID and latest result during the UI session.

### Long-term memory

`memory.py` stores selected customer facts and assessment history in:

```text
app/loan_memory.db
```

The database is created automatically on first use.

Only useful business facts/results are persisted. The complete LangGraph state is **not** blindly stored.

## Run

### 1. Build the sandbox image

```powershell
docker build -t loan-calculation-sandbox ./sandbox
```

### 2. Create Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Run the CLI

```powershell
python main.py
```

### 4. Run Streamlit

```powershell
streamlit run ui/app.py
```

## How to demonstrate memory

1. Run the Streamlit application.
2. Use customer ID `CUST001`.
3. Run an assessment.
4. The result is persisted in `app/loan_memory.db`.
5. Submit another assessment using `CUST001`.
6. The UI will show **Previous Assessments** and the stored **Long-Term Customer Memory**.
7. Try a new customer ID to see that memory is separate per customer.

## Interview explanation

> "I separate workflow state from persistent memory. LangGraph LoanState manages the current execution state across agents. Streamlit session state maintains the current UI workflow. For long-term customer memory, I persist selected business facts and assessment history in SQLite and load that memory at the beginning of the workflow. After a successful assessment, the memory node persists the relevant outcome. This prevents us from blindly storing the entire workflow state and gives us a clear memory boundary."

## Production considerations

SQLite is intentionally used here because this is a local POC. For production, the memory layer can be replaced with PostgreSQL, Redis, or another managed store. Sensitive customer data should have encryption, access control, retention policies, audit logging, and PII controls.

The Docker sandbox is also a learning POC, not a production-grade arbitrary-code execution environment. In production, prefer a fixed calculator API/function, strict input validation, stronger isolation, secret isolation, audit logging, and policy enforcement.
