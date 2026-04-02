from pathlib import Path
from datetime import datetime

VAULT_PATH = r"C:\Users\DELL\Documents\AI_Employee_Vault"

def generate_briefing():
    vault = Path(VAULT_PATH)
    done_files = list((vault / 'Done').glob('*.md'))
    pending = list((vault / 'Needs_Action').glob('*.md'))
    
    briefing = f'''---
generated: {datetime.now().isoformat()}
---
# Monday Morning CEO Briefing

## Summary
- Completed tasks this week: {len(done_files)}
- Still pending: {len(pending)}

## Completed Tasks
'''
    for f in done_files[-5:]:
        briefing += f'- [x] {f.stem}\n'
    
    if not done_files:
        briefing += '- No completed tasks yet\n'
    
    briefing += '\n## Pending Actions\n'
    for f in pending[:5]:
        briefing += f'- [ ] {f.stem}\n'
    
    if not pending:
        briefing += '- No pending actions\n'
    
    briefing += '\n## Suggestions\n- Review pending approvals\n- Check audit logs\n'
    
    out = vault / 'Briefings' / f'{datetime.now().strftime("%Y-%m-%d")}_Briefing.md'
    out.write_text(briefing)
    print(f"Briefing generated: {out.name}")

generate_briefing()