from graph_client import graph, find_group, DEPARTMENT_GROUPS

for dept, name in DEPARTMENT_GROUPS.items():
    existing = find_group(name)
    if existing:
        print(f"Exists:  {name} ({existing['id']})")
        continue
    resp = graph(
        "POST",
        "/groups",
        json={
            "displayName": name,
            "description": f"IAM-Ops {dept} access group",
            "mailEnabled": False,
            "mailNickname": name.lower().replace("-", ""),
            "securityEnabled": True,
        },
    )
    if resp.status_code == 201:
        print(f"Created: {name} ({resp.json()['id']})")
    else:
        print(f"Failed:  {name} -> {resp.status_code} {resp.text}")
