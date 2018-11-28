import os
import tempfile 

import pytest

import opusrepository

@pytest.fixture
def client():
    opusrepository.app.config['TESTING'] = True
    client = opusrepository.app.test_client()

    yield client

def login(client, username, password):
    return client.post('/login/', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

def logout(client):
    return client.get('/logout', follow_redirects=True)

def test_login_logout(client):
    rv = login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    assert b'You are now logged in' in rv.data
    rv = logout(client)
    assert b'You have been logged out!' in rv.data
    rv = login(client, os.environ["TESTUSER"], "wrongpassword")
    assert b'Invalid credentials, try again.' in rv.data
    rv = login(client, "wrongusername", os.environ["TESTPW"])
    assert b'Invalid credentials, try again.' in rv.data

def test_registering(client):
    rv = client.get('/register/')
    assert b'Register' in rv.data
    rv = client.post('/register/', data=dict(
        username = "123test456user789",
        email = "123test456user789",
        password = "123test456user789",
        confirm = "123test456user789"
    ), follow_redirects=True)
    print(rv.data)
    assert b'Thanks for registering!' in rv.data
    c, conn = opusrepository.connection()
    c.execute("DELETE FROM users WHERE username = (%s)", "123test456user789")
    conn.commit()
    c.close()
    conn.close()

def test_access_frontpage(client):
    rv = client.get('/', follow_redirects=True)
    assert b'You need to login first' in rv.data and b'type="submit" value="Login"' in rv.data
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get('/', follow_redirects=True)
    assert b'My corpora' in rv.data and b'My groups' in rv.data
