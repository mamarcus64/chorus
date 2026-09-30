def test_registration_key_and_session(client):
    rejected = client.post(
        "/api/p/voices/auth/register",
        json={"username": "ada", "password": "password1", "registration_key": "nope"},
    )
    assert rejected.status_code == 403

    anon = client.get("/api/p/voices/auth/me")
    assert anon.status_code == 401

    created = client.post(
        "/api/p/voices/auth/register",
        json={"username": "ada", "password": "password1", "registration_key": "test-reg-key"},
    )
    assert created.status_code == 200
    assert created.json()["username"] == "ada"
    assert created.json()["is_admin"] is False

    me = client.get("/api/p/voices/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "ada"

    client.post("/api/p/voices/auth/logout")
    assert client.get("/api/p/voices/auth/me").status_code == 401

    bad = client.post(
        "/api/p/voices/auth/login",
        json={"username": "ada", "password": "wrong-password"},
    )
    assert bad.status_code == 401

    good = client.post(
        "/api/p/voices/auth/login",
        json={"username": "ada", "password": "password1"},
    )
    assert good.status_code == 200
    assert client.get("/api/p/voices/home").status_code == 200


def test_unknown_project_is_404(client):
    response = client.get("/api/p/other/auth/me")
    assert response.status_code == 404
