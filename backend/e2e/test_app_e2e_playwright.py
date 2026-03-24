from __future__ import annotations

import requests
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, expect


def _register_and_create_character(
    page: Page,
    frontend_url: str,
    user: Any,
    *,
    character_name: str,
    faction_button: str,
    backstory: str,
) -> None:
    page.goto(frontend_url)
    expect(page.get_by_role("heading", name="Aerus Game Master Platform")).to_be_visible()

    page.get_by_label("Invite code").fill(user.invite_code)
    page.get_by_label("Username").fill(user.username)
    page.get_by_label("Password").fill(user.password)
    page.get_by_role("button", name="Entrar no mundo").click()

    expect(page).to_have_url(f"{frontend_url}/character", timeout=20000)
    page.get_by_label("Nome").fill(character_name)
    page.get_by_label("Raça").select_option("humano")
    page.get_by_role("button", name=faction_button).click()
    page.get_by_label("Backstory").fill(backstory)
    page.get_by_role("button", name="Entrar no mundo").click()
    expect(page).to_have_url(f"{frontend_url}/game", timeout=90000)
    _dismiss_isekai_intro_if_present(page)
    _assert_game_shell_loaded(page)


def _open_summary_tab(page: Page) -> None:
    summary_button = page.get_by_role("button", name="Resumo")
    if summary_button.count() > 0:
        summary_button.first.click()


def _assert_coop_section(page: Page) -> None:
    section = page.locator("section").filter(has_text="Missão Cooperativa Inicial")
    expect(section).to_be_visible()
    expect(section.get_by_text("Local compartilhado:")).to_be_visible()
    expect(section.get_by_text("Ilhas de Myr", exact=True)).to_be_visible()


def _get_access_token(page: Page) -> str:
    token = page.evaluate("() => localStorage.getItem('aerus_token')")
    assert isinstance(token, str) and token
    return token


def _fetch_debug_snapshot(
    http_client: requests.Session,
    backend_url: str,
    access_token: str,
) -> dict:
    response = http_client.get(
        f"{backend_url}/debug/state",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _create_context_and_page(browser: Browser, timeout_ms: int) -> tuple[BrowserContext, Page]:
    context = browser.new_context()
    context.set_default_timeout(timeout_ms)
    context.set_default_navigation_timeout(timeout_ms)
    return context, context.new_page()


def _dismiss_isekai_intro_if_present(page: Page) -> None:
    enter_button = page.get_by_role("button", name="Entrar em Aerus")
    if enter_button.count() > 0 and enter_button.first.is_visible():
        enter_button.first.click()


def _assert_game_shell_loaded(page: Page) -> None:
    expect(page.locator(".narrative")).to_be_visible()
    expect(page.locator(".sheet")).to_be_visible()
    expect(page.get_by_role("button", name="Enviar")).to_be_visible()
    expect(page.locator(".connection-status")).to_be_visible()
    expect(page.get_by_role("button", name="Debug")).to_be_visible()


def _open_debug_and_validate_snapshot(page: Page) -> None:
    page.get_by_role("button", name="Debug").click()
    snapshot_button = page.get_by_role("button", name="Snapshot")
    expect(snapshot_button).to_be_visible()
    snapshot_button.click()

    compare_block = page.get_by_text("Comparação backend vs frontend")
    expect(compare_block).to_be_visible()

    consistent = page.get_by_text("Estado local consistente com snapshot do backend.")
    diff_list = page.locator(".debug-diff-list")
    expect(consistent.or_(diff_list)).to_be_visible()


def _create_macro_and_send_action(page: Page) -> None:
    page.get_by_role("button", name="Macros").click()

    page.get_by_placeholder("/nome-macro").fill("/golpe")
    page.get_by_placeholder("Descreva a ação que será expandida ao usar o comando").fill(
        "Eu avanço com um corte diagonal e recuo para guarda alta."
    )
    page.get_by_role("button", name="Salvar macro").click()
    expect(page.get_by_text("Salvo!")).to_be_visible()

    action_input = page.get_by_placeholder("Descreva sua ação... (ou use /macro)")
    action_input.fill("/golpe")
    page.get_by_role("button", name="Enviar").click()

    expect(page.get_by_text("Aguardando outros jogadores...")).to_be_visible()
    expect(action_input).to_have_value("")


def _validate_byok_panel(page: Page) -> None:
    byok_toggle = page.get_by_label("Configurações BYOK")
    byok_toggle.dispatch_event("click")
    page.get_by_role("button", name="Salvar chave").click()
    expect(page.get_by_text("Informe uma chave válida.")).to_be_visible()


def _validate_volume_panel(page: Page) -> None:
    volume_toggle = page.get_by_label("Configurações de volume")
    volume_toggle.dispatch_event("click")
    sliders = page.locator(".volume-panel input[type='range']")
    expect(sliders).to_have_count(3)



def test_full_e2e_flow_via_frontend(
    page: Page,
    e2e_config,
    test_user,
) -> None:
    page.goto(e2e_config.frontend_url)

    expect(page.get_by_role("heading", name="Aerus Game Master Platform")).to_be_visible()

    page.get_by_label("Invite code").fill(test_user.invite_code)
    page.get_by_label("Username").fill(test_user.username)
    page.get_by_label("Password").fill(test_user.password)
    page.get_by_role("button", name="Entrar no mundo").click()

    expect(page).to_have_url(f"{e2e_config.frontend_url}/character", timeout=15000)

    page.get_by_label("Nome").fill("Kael E2E")
    page.get_by_label("Raça").select_option("elfo")
    page.get_by_role("button", name="Guilda dos Fios\nMisterioso e acadêmico.").click()
    page.get_by_label("Backstory").fill(
        "Fui arrancado da minha realidade durante uma tempestade arcana e acordei em Aerus com ecos de memórias fragmentadas, decidido a sobreviver e descobrir a verdade do Fio."  # noqa: E501
    )
    page.get_by_role("button", name="Entrar no mundo").click()

    expect(page).to_have_url(f"{e2e_config.frontend_url}/game", timeout=90000)

    _dismiss_isekai_intro_if_present(page)
    _assert_game_shell_loaded(page)

    _validate_volume_panel(page)
    _validate_byok_panel(page)
    _open_debug_and_validate_snapshot(page)
    _create_macro_and_send_action(page)

    page.reload()
    expect(page.locator(".connection-status")).to_be_visible()
    _dismiss_isekai_intro_if_present(page)
    _open_debug_and_validate_snapshot(page)


def test_multiplayer_cooperative_mission_flow(
    browser: Browser,
    e2e_config,
    http_client: requests.Session,
    make_test_user,
) -> None:
    user_a = make_test_user("e2e_coop_a")
    user_b = make_test_user("e2e_coop_b")

    context_a, page_a = _create_context_and_page(browser, e2e_config.timeout_ms)
    context_b, page_b = _create_context_and_page(browser, e2e_config.timeout_ms)

    try:
        _register_and_create_character(
            page_a,
            e2e_config.frontend_url,
            user_a,
            character_name="Kael Coop A",
            faction_button="Guilda dos Fios\nMisterioso e acadêmico.",
            backstory=(
                "Despertei em Aerus com memórias quebradas e um chamado insistente para"
                " reunir aliados antes que o Fio se rompa de vez."
            ),
        )
        _register_and_create_character(
            page_b,
            e2e_config.frontend_url,
            user_b,
            character_name="Lyra Coop B",
            faction_button="Império de Valdrek\nMilitar e imponente.",
            backstory=(
                "Ouvi vozes no limiar entre mundos e atravessei o véu para Aerus com"
                " a certeza de que só um pacto coletivo impedirá a ruína final."
            ),
        )

        _open_summary_tab(page_a)
        _open_summary_tab(page_b)
        _assert_coop_section(page_a)
        _assert_coop_section(page_b)

        token_a = _get_access_token(page_a)
        _ = _fetch_debug_snapshot(
            http_client,
            e2e_config.backend_url,
            token_a,
        )

        action_a = page_a.get_by_placeholder("Descreva sua ação... (ou use /macro)")
        action_b = page_b.get_by_placeholder("Descreva sua ação... (ou use /macro)")
        action_a.fill("Examino o selo antigo no centro de Ilhas de Myr e convoco o grupo.")
        page_a.get_by_role("button", name="Enviar").click()
        action_b.fill("Uno minha energia ao ritual do grupo para estabilizar o primeiro selo.")
        page_b.get_by_role("button", name="Enviar").click()

        token_b = _get_access_token(page_b)
        snapshot_a = _fetch_debug_snapshot(
            http_client,
            e2e_config.backend_url,
            token_a,
        )
        snapshot_b = _fetch_debug_snapshot(
            http_client,
            e2e_config.backend_url,
            token_b,
        )

        _open_summary_tab(page_a)
        _open_summary_tab(page_b)
        expect(page_a.get_by_text("Status:")).to_be_visible(timeout=20000)
        expect(page_b.get_by_text("Status:")).to_be_visible(timeout=20000)

        flags_a = snapshot_a.get("quest_flags", {})
        flags_b = snapshot_b.get("quest_flags", {})
        required_players_a = int(flags_a.get("cooperative_mission_required_players", "0") or 0)
        required_players_b = int(flags_b.get("cooperative_mission_required_players", "0") or 0)

        assert required_players_a >= 2
        assert required_players_b >= 2
        assert "cooperative_mission_active" in flags_a
        assert "cooperative_mission_completed" in flags_a
        assert "cooperative_mission_blocking" in flags_a
        assert "cooperative_mission_completed_players" in flags_a
        assert "cooperative_mission_objective" in flags_a
    finally:
        context_a.close()
        context_b.close()


def test_scaling_preview_increases_from_solo_to_group(
    browser: Browser,
    e2e_config,
    http_client: requests.Session,
    make_test_user,
) -> None:
    user_solo = make_test_user("e2e_scale_solo")
    user_b = make_test_user("e2e_scale_b")
    user_c = make_test_user("e2e_scale_c")

    context_solo, page_solo = _create_context_and_page(browser, e2e_config.timeout_ms)
    context_b, page_b = _create_context_and_page(browser, e2e_config.timeout_ms)
    context_c, page_c = _create_context_and_page(browser, e2e_config.timeout_ms)

    try:
        _register_and_create_character(
            page_solo,
            e2e_config.frontend_url,
            user_solo,
            character_name="Solo Scale",
            faction_button="Igreja da Chama Pura\nSagrado e austero.",
            backstory=(
                "Cheguei sozinho em Aerus, mas sinto que a pressão das batalhas muda"
                " quando mais convocados se unem na mesma mesa."
            ),
        )

        token_solo = _get_access_token(page_solo)
        snapshot_before = _fetch_debug_snapshot(http_client, e2e_config.backend_url, token_solo)
        runtime_before = snapshot_before.get("runtime", {})
        alive_before = int(runtime_before.get("alive_players", 0) or 0)
        scale_before = float(runtime_before.get("encounter_scale_preview", 1.0) or 1.0)
        boss_steps_before = int(runtime_before.get("boss_scale_steps_preview", 0) or 0)

        _register_and_create_character(
            page_b,
            e2e_config.frontend_url,
            user_b,
            character_name="Group Scale B",
            faction_button="Guilda dos Fios\nMisterioso e acadêmico.",
            backstory=(
                "Meu papel é coordenar o grupo em conflitos maiores para observar como"
                " a dificuldade se adapta à presença coletiva na mesa."
            ),
        )
        _register_and_create_character(
            page_c,
            e2e_config.frontend_url,
            user_c,
            character_name="Group Scale C",
            faction_button="Império de Valdrek\nMilitar e imponente.",
            backstory=(
                "Entrei para reforçar a formação e medir como o ritmo de combate se"
                " intensifica com mais aventureiros ativos."
            ),
        )

        snapshot_after = _fetch_debug_snapshot(http_client, e2e_config.backend_url, token_solo)
        runtime_after = snapshot_after.get("runtime", {})
        alive_after = int(runtime_after.get("alive_players", 0) or 0)
        scale_after = float(runtime_after.get("encounter_scale_preview", scale_before) or scale_before)
        boss_steps_after = int(runtime_after.get("boss_scale_steps_preview", boss_steps_before) or boss_steps_before)

        assert alive_after >= alive_before + 2
        assert scale_after > scale_before
        assert boss_steps_after >= boss_steps_before + 1
    finally:
        context_solo.close()
        context_b.close()
        context_c.close()
