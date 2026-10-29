"""Bounded adapter interface. This implementation makes no external AI calls."""
from typing import Protocol
class AssistantAdapter(Protocol):
    def summarize(self,evidence:dict)->dict: ...
class DemonstrationAssistant:
    def summarize(self,evidence):
        return {'mode':'Demonstration assistant — deterministic template; no live AI','text':f"[{evidence['id']}] {evidence['title']}: {evidence['result']} Provenance: {evidence['type']}. Verification: {evidence['verification']}. Limitations: {evidence['limitations']}. Applicability needs human confirmation; this summary is not new evidence.",'references':[evidence['id']],'uncertainty':'No independent model or supplier validation performed.','requires_human_confirmation':True}
assistant=DemonstrationAssistant()
