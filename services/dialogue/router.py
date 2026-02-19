from services.extraction.ollama_client import extract_slots_with_ollama, extract_clinic_info
from services.dialogue.routes import handle_emergency, handle_appointment, handle_info, handle_cancel_appointment

def run_dialogue_logic(user_text, intent):
    
    # 1. Redirection vers les urgences (Priorité maximale)
    if intent == "medical_urgency":
        return handle_emergency(user_text)

    # 2. Prise de RDV 
    elif intent == "book_appointment":
        slots = extract_slots_with_ollama(user_text)
        return handle_appointment(slots)

    # 3. Annulation de RDV 
    elif intent == "cancel_appointment":
        slots = extract_slots_with_ollama(user_text)
        return handle_cancel_appointment(slots)

    # 4. Demande d'information
    elif intent == "info_practical":
        info_result = extract_clinic_info(user_text)
        info_type = info_result.get("requested_info", "other") if isinstance(info_result, dict) else info_result
        return handle_info(user_text, info_type)

    # 5. Fallback (Hors sujet ou non compris)
    if intent == "off_topic":
        return "Désolé, je ne suis pas sûr de comprendre. Pouvez-vous reformuler ?"