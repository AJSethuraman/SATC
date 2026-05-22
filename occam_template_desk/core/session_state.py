from __future__ import annotations

GENERATION_STATE_KEY = "occam_generation_result"


def build_generation_state(package: dict, rendered_email: dict | None, validation: dict, selected_template: str, selected_client: dict, final_values: dict) -> dict:
    return {
        "package": package,
        "rendered_email": rendered_email,
        "validation": validation,
        "selected_template": selected_template,
        "selected_client": selected_client,
        "final_values": final_values,
    }


def save_generation_state(state_store: dict, package: dict, rendered_email: dict | None, validation: dict, selected_template: str, selected_client: dict, final_values: dict) -> dict:
    state = build_generation_state(package, rendered_email, validation, selected_template, selected_client, final_values)
    state_store[GENERATION_STATE_KEY] = state
    return state


def get_generation_state(state_store: dict) -> dict | None:
    return state_store.get(GENERATION_STATE_KEY)


def clear_generation_state(state_store: dict) -> None:
    state_store.pop(GENERATION_STATE_KEY, None)
