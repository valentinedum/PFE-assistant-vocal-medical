import json
from services.extraction.ollama_client import (
    extract_slots_with_ollama,
    extract_clinic_info,
    extract_confirmation,
)
from services.dialogue.routes import (
    handle_emergency,
    handle_appointment,
    handle_info,
    handle_cancel_appointment,
)

ACTION_HANDLERS = {
    "book_appointment": handle_appointment,
    "cancel_appointment": handle_cancel_appointment,
}

def run_dialogue_logic(user_text, intent, context_json=None):

    # 1. CONFIRMATION (Si une action est en attente de confirmation, on la traite avant tout autre intent)
    pending_action = None
    if context_json:
        try:
            pending_action = json.loads(context_json)
        except:
            pass
    
    if pending_action:
        confirmation = extract_confirmation(user_text).get("confirmation")

        if confirmation == "oui":
            action = pending_action.get("type")
            slots = pending_action.get("slots")

            handler_function = ACTION_HANDLERS.get(action)
            if handler_function:
                result = handler_function(slots, confirmation=True)
                return {"response": result.get("message"), "context": None, "intent": action}
            
        elif confirmation == "non":
            return {"response": "D'accord, rendez-vous non confirmé. Si vous voulez autre chose, n'hésitez pas à demander.", "context": None}
        else:
            return {"response": "Je n'ai pas compris votre confirmation. Veuillez répondre par 'oui' ou 'non'.", "context": context_json}
    
    # 2. Si pas d'action en attente, on traite selon l'intent détecté
    # Redirection vers les urgences (Priorité maximale)
    if intent == "medical_urgency":
        return {"response": handle_emergency(user_text), "context": None}

    # Prise de RDV ou Annulation de RDV
    elif intent in ACTION_HANDLERS:
        slots = extract_slots_with_ollama(user_text)

        handler_function = ACTION_HANDLERS.get(intent)
        result = handler_function(slots, confirmation=False)

        new_context = None
        message = result.get("message")
        if result.get("needs_confirmation"):
            new_context = json.dumps({"type": "cancel_appointment", "slots": slots})

        return {"response": message, "context": new_context}
        
    # Demande d'information
    elif intent == "info_practical":
        info_result = extract_clinic_info(user_text)
        info_type = (
            info_result.get("requested_info", "other")
            if isinstance(info_result, dict)
            else info_result
        )
        return {"response": handle_info(user_text, info_type), "context": None}

    # Fallback (Hors sujet ou non compris)
    if intent == "off_topic":
        return {"response": "Désolé, je ne suis pas sûr de comprendre. Pouvez-vous reformuler ?", "context": None}
