"""Atleta sin código: cuenta personal gratuita, aislada, y unirse después a un coach."""


def test_registro_sin_codigo_crea_una_cuenta_personal(atleta_solo):
    assert atleta_solo.datos["role"] == "athlete"
    assert atleta_solo.datos["box"]["kind"] == "athlete"
    assert atleta_solo.datos["box"]["status"] == "active"
    assert atleta_solo.datos["coach_id"] is None


def test_registrar_dos_veces_el_mismo_correo_no_revela_ni_duplica(client, atleta_solo):
    cuerpo = {"email": atleta_solo.email, "full_name": "Otra Persona", "password": "password123"}
    primero = client.post("/auth/register", json=cuerpo)
    segundo = client.post("/auth/register", json=cuerpo)
    assert primero.status_code == 200 and primero.json() == segundo.json()


def test_no_ve_clases_ni_comparte_cuenta_con_otros(atleta_solo):
    assert atleta_solo.get("/classes/").status_code == 403
    assert atleta_solo.get("/boxes/me").json()["invite_code"] is None


def test_el_codigo_de_una_cuenta_personal_no_sirve_para_unirse(client, atleta_solo, atleta_de_coach):
    # Un atleta solo no puede recibir gente en su cuenta: su "código" interno se rechaza.
    r = client.get(f"/boxes/by-code/{atleta_solo.datos['box']['id'][:8]}")
    assert r.status_code == 400


def test_se_une_a_un_coach_y_conserva_sus_datos(client, coach, codigo_coach, atleta_solo):
    creado = atleta_solo.post("/users/me/personal-sessions", json={"scheduled_date": "2026-01-05"})
    assert creado.status_code == 200, creado.text

    assert atleta_solo.post("/boxes/join", json={"invite_code": "NOEXISTE"}).status_code == 400
    r = atleta_solo.post("/boxes/join", json={"invite_code": codigo_coach})
    assert r.status_code == 200, r.text

    me = atleta_solo.get("/auth/me").json()
    assert me["box"]["id"] == coach.datos["box"]["id"]
    assert len(atleta_solo.get(f"/users/{me['id']}/mesocycles/").json()) >= 1
    # Ya no puede volver a "unirse" a otro sitio por esta ruta.
    assert atleta_solo.post("/boxes/join", json={"invite_code": codigo_coach}).status_code == 400
