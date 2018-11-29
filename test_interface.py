import os
import xml.etree.ElementTree as ET

import pytest

import opusrepository
import xml_parser

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
        username = "",
        email = "123test456user789",
        password = "123test456user789",
        confirm = "123test456user789"
    ), follow_redirects=True)
    assert b'Field must be between 4 and 20 characters long.' in rv.data

    rv = client.post('/register/', data=dict(
        username = "123test456user789",
        email = "",
        password = "123test456user789",
        confirm = "123test456user789"
    ), follow_redirects=True)
    assert b'Field must be between 6 and 50 characters long.' in rv.data

    rv = client.post('/register/', data=dict(
        username = "123test456user789",
        email = "123test456user789",
        password = "123test456user789",
        confirm = ""
    ), follow_redirects=True)
    assert b'Passwords must match' in rv.data

    rv = client.post('/register/', data=dict(
        username = "123test456user789",
        email = "123test456user789",
        password = "123test456user789",
        confirm = "123test456user789"
    ), follow_redirects=True)
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
    
def test_allowed_file():
    extensions = ['pdf', 'doc', 'txt', 'xml', 'html', 'tar', 'gz']
    for extension in extensions:
        print(opusrepository.allowed_file("ajokielto."+extension))
        assert opusrepository.allowed_file("ajokielto."+extension)
    invalid = ["ajokielto.exe", "ajokieltopdf"]
    for i in invalid:
        assert not opusrepository.allowed_file(i)

def test_parseLine():
    parser = xml_parser.XmlParser([])
    result = parser.parseLine('<div test="attribute">hello</div>')
    assert result == ('"div"', '"hello"', '"div"', {'test': 'attribute'})

def test_recursiveGroups():
    parser = xml_parser.XmlParser([])
    parser.recursiveGroups(ET.fromstring(
        '<entry id="mikkotest" kind="user info">\
            <member>mikkotest</member>\
            <my_group>mikkotest</my_group>\
        </entry>'
    ))

    assert len(parser.elementList) == 0
    parser.recursiveGroups(ET.fromstring(
        '<entry id="mikkotest" kind="user info">\
            <member>mikkotest</member>\
            <member_of>mikkotest,public</member_of>\
            <my_group>mikkotest</my_group>\
        </entry>'
    ))
    assert parser.elementList[0] == "mikkotest" and parser.elementList[1] == "public"

def test_groupsForUser():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="group/mikkotest">',
                '<entry id="mikkotest" kind="user info">',
                    '<member>mikkotest</member>',
                    '<member_of>mikkotest,public</member_of>',
                    '<my_group>mikkotest</my_group>',
                '</entry>',
            '</list>',
            '<status code="0" location="/group/mikkotest/" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    groups = parser.groupsForUser()
    assert groups[0] == "mikkotest" and groups[1] == "public"

def test_recursiveCorpora():
    parser = xml_parser.XmlParser([])

    parser.recursiveCorpora(ET.fromstring(
        '<list path="">'\
            '<entry directory="mikkocorpus2/mikkotest" />'\
        '</list>'
    ))
    assert len(parser.elementList) == 0

    parser.recursiveCorpora(ET.fromstring(
        '<list path="">'\
            '<entry path="mikkocorpus/mikkotest" />'\
            '<entry path="mikkocorpus2/mikkotest" />'\
        '</list>'
    ))
    assert parser.elementList[0] == "mikkocorpus" and parser.elementList[1] == "mikkocorpus2"

    parser.recursiveCorpora(ET.fromstring(
        '<list path="">'\
            '<entry path="mikkocorpus/mikkotest" />'\
            '<entry path="mikkocorpus2/mikkotest" />'\
        '</list>'
    ))
    assert len(parser.elementList) == 2 and parser.elementList[0] == "mikkocorpus" and parser.elementList[1] == "mikkocorpus2"
          
