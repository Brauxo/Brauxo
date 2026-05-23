name: System Query (AI Terminal)

description: "Submit a query to Brauxo's Core AI"
title: "[SYSTEM_QUERY] AI Terminal Execution"
labels: question, ai-chat
body:
  - type: markdown
    attributes:
      value: "### >_ [SYSTEM_TERMINAL] ACCESS GRANTED\n\nSubmit your query regarding Owen Braux's Data Platform architecture, Cloud infrastructure, or Artificial Intelligence projects. \n\n*Note: All valid queries and system responses are logged to the public README terminal.*"
  - type: textarea
    id: question
    attributes:
      label: ">> ENTER_QUERY"
      description: "Syntax check: Keep it concise. Private data access is restricted."
      placeholder: "e.g., What technologies did Owen use to build his Bitcoin Analytics Platform?"
    validations:
      required: true
