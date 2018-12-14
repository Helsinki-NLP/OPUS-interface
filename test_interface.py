import os
import xml.etree.ElementTree as ET
import io

import pytest

import opusrepository
import xml_parser
import request_handler
rh = request_handler.RequestHandler()

@pytest.fixture
def client():
    opusrepository.app.config['TESTING'] = True
    client = opusrepository.app.test_client()

    yield client

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
    assert parser.elementList[0] == "mikkotest" 
    assert parser.elementList[1] == "public"

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
    assert groups[0] == "mikkotest" 
    assert groups[1] == "public"

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
    assert parser.elementList[0] == "mikkocorpus" 
    assert parser.elementList[1] == "mikkocorpus2"

    parser.recursiveCorpora(ET.fromstring(
        '<list path="">'\
            '<entry path="mikkocorpus/mikkotest" />'\
            '<entry path="mikkocorpus2/mikkotest" />'\
        '</list>'
    ))
    assert len(parser.elementList) == 2 
    assert parser.elementList[0] == "mikkocorpus" 
    assert parser.elementList[1] == "mikkocorpus2"
      
def test_corporaForUser():
    xml_data = [
        '<letsmt-ws version="56">'\
            '<list path="">'\
                '<entry path="mikkocorpus2/mikkotest" />'\
                '<entry path="mikkocorpus/mikkotest" />'\
            '</list>'\
            '<status code="0" location="/metadata" operation="GET" type="ok">Found 2 matching entries</status>'\
        '</letsmt-ws>'
    ]

    parser = xml_parser.XmlParser(xml_data)
    corpora = parser.corporaForUser()

    assert corpora[0] == "mikkocorpus2" 
    assert corpora[1] == "mikkocorpus"

def test_recursiveCollect():
    element = ET.fromstring(
        '<list path="/mikkocorpus">'\
            '<entry kind="branch" path="/mikkocorpus/mikkotest">'\
                '<name>mikkotest</name>'\
                '<group>public</group>'\
                '<owner>mikkotest</owner>'\
            '</entry>'\
        '</list>'
    )
    parser = xml_parser.XmlParser([])
    parser.recursiveCollect(element, "name")
    assert parser.elementList[-1] == "mikkotest"
    parser.recursiveCollect(element, "group")
    assert parser.elementList[-1] == "public"

def test_collectToList():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/mikkocorpus">',
                '<entry kind="branch" path="/mikkocorpus/mikkotest">',
                    '<name>mikkotest</name>',
                    '<group>public</group>',
                    '<owner>mikkotest</owner>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/mikkocorpus" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ] 

    parser = xml_parser.XmlParser(xml_data)
    elementlist = parser.collectToList("group")
    assert len(elementlist) == 1 
    assert elementlist[0] == "public"

def test_branchesForCorpus():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/mikkocorpus">',
                '<entry kind="branch" path="/mikkocorpus/mikkotest">',
                    '<name>mikkotest</name>',
                    '<group>public</group>',
                    '<owner>mikkotest</owner>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/mikkocorpus" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ] 

    parser = xml_parser.XmlParser(xml_data)
    branches = parser.branchesForCorpus()
    assert len(branches) == 1 
    assert branches[0] == "mikkotest"

def test_getUsers():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/group/">',
                '<entry id="public" kind="group" owner="admin">',
                    '<user>user1</user>',
                    '<user>user2</user>',
                    '<user>user3</user>',
                    '<user>user4</user>',
                '</entry>',
            '</list>',
            '<status code="0" location="/group/public" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    
    parser = xml_parser.XmlParser(xml_data)
    users = parser.getUsers()
    assert len(users) == 4 
    assert users[0] == "user1" 
    assert users[3] == "user4"

def test_navigateDirectory():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/mikkocorpus/mikkotest/uploads">',
                '<entry kind="file">',
                    '<name>html.tar.gz</name>',
                    '<commit revision="HEAD">',
                        '<author>mikkotest</author>',
                        '<date>unknown</date>',
                    '</commit>',
                    '<group>public</group>',
                    '<owner>mikkotest</owner>',
                    '<size>14210</size>',
                '</entry>',
                '<entry kind="dir">',
                      '<name>html</name>',
                      '<commit revision="HEAD">',
                          '<author>mikkotest</author>',
                          '<date>unknown</date>',
                      '</commit>',
                      '<group>public</group>',
                      '<owner>mikkotest</owner>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/mikkocorpus/mikkotest/uploads" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]

    parser = xml_parser.XmlParser(xml_data)
    dirs = parser.navigateDirectory()

    assert len(dirs) == 2
    assert dirs[0][0] == "html.tar.gz"
    assert dirs[0][1] == "file"
    assert dirs[1][0] == "html"
    assert dirs[1][1] == "dir"

def test_getMonolingualAndParallel():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="">',
                '<entry path="mikkocorpus/mikkotest">',
                    '<name>mikkotest</name>',
                    '<gid>public</gid>',
                    '<import_queue></import_queue>',
                    '<langs>fi,en,sv</langs>',
                    '<modif>2018-11-27 14:05:14</modif>',
                    '<origin></origin>',
                    '<owner>mikkotest</owner>',
                    '<parallel-langs>fi-sv,en-fi,en-sv</parallel-langs>',
                '</entry>',
            '</list>',
            '<status code="0" location="/metadata/mikkocorpus/mikkotest" operation="GET" type="ok">Found matching path ID. Listing all of its properties</status>',
        '</letsmt-ws>'
    ]

    parser = xml_parser.XmlParser(xml_data)
    mopa = parser.getMonolingualAndParallel()
    assert len(mopa[0]) == 3
    assert len(mopa[1]) == 3
    for lan in [["fi", "dir"], ["sv", "dir"], ["en", "dir"]]:
        assert lan in mopa[0]
    for lan in [["fi-sv", "dir"], ["en-sv", "dir"], ["en-fi", "dir"]]:
        assert lan in mopa[1]

def test_recursiveMetadata():
    element = ET.fromstring(
        '<entry path="mikkocorpus/mikkotest/uploads/html.tar.gz">'\
              '<description>test</description>'\
              '<direction>unknown</direction>'\
              '<gid>public</gid>'\
              '<owner>mikkotest</owner>'\
              '<status>job canceled</status>'\
        '</entry>'
    )

    parser = xml_parser.XmlParser([])
    parser.recursiveMetadata(element)
    correct = {
        "description": "test",
        "direction": "unknown",
        "gid": "public",
        "owner": "mikkotest",
        "status": "job canceled"
    }
    for key in correct.keys():
        assert parser.elementDict[key] == correct[key]

def test_getMetadata():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="">',
            '<entry path="mikkocorpus/mikkotest/uploads/html.tar.gz">',
                  '<description>test</description>',
                  '<direction>unknown</direction>',
                  '<gid>public</gid>',
                  '<owner>mikkotest</owner>',
                  '<status>job canceled</status>',
            '</entry>',
            '</list>',
            '<status code="0" location="/metadata/mikkocorpus/mikkotest/uploads/html.tar.gz" operation="GET" type="ok">Found matching path ID. Listing all of its properties</status>',
        '</letsmt-ws>'
    ]

    parser = xml_parser.XmlParser(xml_data)
    metadata = parser.getMetadata()
    correct = {
        "description": "test",
        "direction": "unknown",
        "gid": "public",
        "owner": "mikkotest",
        "status": "job canceled"
    }
    for key in correct.keys():
        assert metadata[key] == correct[key]

def test_getAlignmentCandidates():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="mikkocorpus/mikkotest/">',
                '<entry path="mikkocorpus/mikkotest/xml/en/html/ajokielto.xml">',
                    '<align-candidates>xml/fi/html/ajokielto.xml</align-candidates>',
                    '<aligned_with>xml/fi/html/ajokielto.xml,xml/sv/html/ajokielto.xml</aligned_with>',
                    '<gid>public</gid>',
                    '<imported_from>uploads/html.tar.gz:html/en/ajokielto.html</imported_from>',
                    '<language>en</language>',
                    '<owner>mikkotest</owner>',
                    '<parsed>ud/en/html/ajokielto.xml</parsed>',
                    '<resource-type>corpusfile</resource-type>',
                    '<size>38</size>',
                    '<status>successfully aligned with mikkocorpus/mikkotest/xml/sv/html/ajokielto.xml</status>',
                '</entry>',
            '</list>',
            '<status code="0" location="/metadata/mikkocorpus/mikkotest" operation="GET" type="ok">Found 1 matching entries</status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    candidates = parser.getAlignCandidates()
    correct = {'en/html/ajokielto.xml': ['fi/html/ajokielto.xml']}

    for key in correct.keys():
        for item in correct[key]:
            assert item in candidates[key]

def test_recursiveAttrTag():
    element = ET.fromstring(
        '<list path="/group/">'\
            '<entry id="mikkotest" kind="group" owner="mikkotest" testattr="testvalue">'\
                '<user>mikkotest</user>'\
            '</entry>'\
        '</list>'
    )
    parser = xml_parser.XmlParser([])
    parser.recursiveAttrTag(element, "entry", "testattr")
    
    assert parser.elementString == "testvalue"

def test_getAttrFromTag():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/group/">',
                '<entry id="mikkotest" kind="group" owner="mikkotest" testattr="testvalue">',
                    '<user>mikkotest</user>',
                '</entry>',
            '</list>',
            '<status code="0" location="/group/mikkotest" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    assert parser.getAttrFromTag("entry", "testattr") == "testvalue"

def test_getGroupOwner():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/group/">',
                '<entry id="mikkotest" kind="group" owner="mikkotest" testattr="testvalue">',
                    '<user>mikkotest</user>',
                '</entry>',
            '</list>',
            '<status code="0" location="/group/mikkotest" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    assert parser.getGroupOwner() == "mikkotest"

def test_getJobs():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="jobs">',
                '<entry name="job_1543831841_642742498" file="mikkocorpus/mikkotest/uploads/html.tar.gz" id="890" job="mikkocorpus/mikkotest/jobs/import/uploads/html.tar.gz.xml" status="RUNNING" />',
            '</list>',
            '<status code="0" location="job" operation="GET" type="ok" />',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    jobs = parser.getJobs()
    assert jobs[0][0] == "mikkocorpus/mikkotest/uploads/html.tar.gz"
    assert jobs[0][1] == "RUNNING"
    
def test_getFileContent():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml">',
                '<entry><?xml version="1.0" encoding="utf-8"?>',
                '<letsmt version="1.0">',
                '<p id="1">',
                '<s id="1">If a person is sentenced to a punishment for causing a serious traffic hazard, driving while intoxicated or driving while seriously intoxicated, the court also imposes a driving ban for at most five years.</s>',
                '</p>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    content = parser.getFileContent()

    correct = '<?xml version="1.0" encoding="utf-8"?>\n'\
    '<letsmt version="1.0">\n'\
    '<p id="1">\n'\
    '<s id="1">If a person is sentenced to a punishment for causing a serious traffic hazard, driving while intoxicated or driving while seriously intoxicated, the court also imposes a driving ban for at most five years.</s>\n'\
    '</p>\n'

    assert content == correct

def test_itemExists():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/mikkocorpus">',
                '<entry kind="branch" path="/mikkocorpus/mikkotest">',
                    '<name>mikkotest</name>',
                    '<group>public</group>',
                    '<owner>mikkotest</owner>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/mikkocorpus" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    
    assert parser.itemExists() == True
        
    xml_data = [
        '<letsmt-ws version="56">',
            '''<status code="6" location="/storage/mikkocorpusdoesnotexist" operation="GET" type="error">Cannot find/read slot 'mikkocorpusdoesnotexist'</status>''',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)

    assert parser.itemExists() == False
    
def test_rh_get_storage():
    response = rh.get("/storage/mikkocorpus/mikkotest", {"uid": "mikkotest"})
    texts = [
        '<letsmt-ws version="56">',
        '<list path="/mikkocorpus/mikkotest">',
        '<name>uploads</name>',
        '<name>xml</name>',
        '<status code="0" location="/storage/mikkocorpus/mikkotest" operation="GET" type="ok"></status>'
    ]
    for text in texts:
        assert text in response

def test_rh_get_download():
    response = rh.get("/storage/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml", {"uid": "mikkotest", "action": "download", "archive": "0"})
    texts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<letsmt version="1.0">',
        '<s id="2">The police may impose a driving ban also for other violations.</s>',
        '<s id="38">European Court of Human Rights</s>',
        '</letsmt>'
    ]
    for text in texts:
        assert text in response

def test_rh_get_getFileContent():
    response = rh.get("/storage/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml", {"uid": "mikkotest", "action": "cat", "to": "1"})
    assert len(response.split("\n")) == 9
    response = rh.get("/storage/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml", {"uid": "mikkotest", "action": "cat", "to": "5"})
    assert len(response.split("\n")) == 13
    assert '<s id="1">If a person is sentenced to a punishment for causing a serious traffic hazard, driving while intoxicated or driving while seriously intoxicated, the court also imposes a driving ban for at most five years.</s>' in response

def test_rh_post():
    rh.post("/metadata/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml", {"uid": "mikkotest", "testkey": "testvalue"})
    xml_metadata = rh.get("/metadata/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml", {"uid": "mikkotest"})
    parser = xml_parser.XmlParser(xml_metadata.split("\n"))
    metadata = parser.getMetadata()
    assert metadata["testkey"] == "testvalue"
    rh.post("/metadata/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml", {"uid": "mikkotest", "testkey": "testvalue2"})
    xml_metadata = rh.get("/metadata/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml", {"uid": "mikkotest"})
    parser = xml_parser.XmlParser(xml_metadata.split("\n"))
    metadata = parser.getMetadata()
    assert metadata["testkey"] == "testvalue2"

def test_rh_put():
    rh.post("/metadata/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml", {"uid": "mikkotest", "testkey": "testvalue"})
    xml_metadata = rh.get("/metadata/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml", {"uid": "mikkotest"})
    parser = xml_parser.XmlParser(xml_metadata.split("\n"))
    metadata = parser.getMetadata()
    assert metadata["testkey"] == "testvalue"
    rh.put("/metadata/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml", {"uid": "mikkotest", "testkey": "testvalue2"})
    xml_metadata = rh.get("/metadata/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml", {"uid": "mikkotest"})
    parser = xml_parser.XmlParser(xml_metadata.split("\n"))
    metadata = parser.getMetadata()
    assert "testvalue" in metadata["testkey"] and "testvalue2" in metadata["testkey"]

def test_rh_upload_and_delete():
    response = rh.upload("/storage/mikkocorpus/mikkotest/uploads/test/test.txt", {"uid": "mikkotest"}, opusrepository.UPLOAD_FOLDER+"/test.txt")
    assert '<status code="0" location="/storage/mikkocorpus/mikkotest/uploads/test/test.txt" operation="PUT" type="ok">update ok /mikkocorpus/mikkotest/uploads/test/test.txt</status>' in response
    response = rh.get("/storage/mikkocorpus/mikkotest/uploads/test/test.txt", {"uid": "mikkotest"})
    assert '<name>test.txt</name>' in response 
    response = rh.delete("/storage/mikkocorpus/mikkotest/uploads/test/test.txt", {"uid": "mikkotest"})
    assert '<status code="0" location="/storage/mikkocorpus/mikkotest/uploads/test/test.txt" operation="DELETE" type="ok">Deleted /storage/mikkocorpus/mikkotest/uploads/test/test.txt</status>' in response
    response = rh.get("/storage/mikkocorpus/mikkotest/uploads/test/test.txt", {"uid": "mikkotest"})
    assert '<name>test.txt</name>' not in response 

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

def test_allowed_file():
    extensions = ['pdf', 'doc', 'txt', 'xml', 'html', 'tar', 'gz']
    for extension in extensions:
        print(opusrepository.allowed_file("ajokielto."+extension))
        assert opusrepository.allowed_file("ajokielto."+extension)
    invalid = ["ajokielto.exe", "ajokieltopdf"]
    for i in invalid:
        assert not opusrepository.allowed_file(i)

def test_get_group_owner():
    assert opusrepository.get_group_owner("mikkotest", "mikkotest") == "mikkotest"

def test_access_frontpage(client):
    rv = client.get('/', follow_redirects=True)
    assert b'You need to login first' in rv.data 
    assert b'type="submit" value="Login"' in rv.data
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get('/', follow_redirects=True)
    assert b'My corpora' in rv.data 
    assert b'My groups' in rv.data

def test_create_corpus(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rh.delete("/storage/1233test_corpus5678", {"uid": os.environ["TESTUSER"]})
    rv = client.get('/create_corpus')
    assert b'Create Corpus' in rv.data
    post_data = {
        "name": "",
        "group": "group",
        "domain": "domain",
        "origin": "origin",
        "description": "description",
        "pdf_reader": "pdf_reader",
        "document_alignment": "document_alignment",
        "sentence_alignment": "sentence_alignment",
        "sentence_splitter": "sentence_splitter",
        "autoalignment": "on"
    }
    rv = client.post('/create_corpus', data=post_data, follow_redirects=True)
    assert b'Name must be ASCII only and must not contain spaces' in rv.data
    post_data["name"] = "with space"
    rv = client.post('/create_corpus', data=post_data, follow_redirects=True)
    assert b'Name must be ASCII only and must not contain spaces' in rv.data
    post_data["name"] = "1233test_corpus5678"
    rv = client.post('/create_corpus', data=post_data, follow_redirects=True)
    assert b'Corpus &#34;1233test_corpus5678&#34; created!' in rv.data
    xml_metadata = rh.get("/metadata/1233test_corpus5678/"+os.environ["TESTUSER"], {"uid": os.environ["TESTUSER"]})
    parser = xml_parser.XmlParser(xml_metadata.split("\n"))
    metadata = parser.getMetadata()
    field_dict = opusrepository.initialize_field_dict()
    for key in post_data.keys():
        if key != "name":
            assert post_data[key] == metadata[field_dict[key][0]]
    rv = client.post('/create_corpus', data=post_data, follow_redirects=True)
    assert b'Corpus &#34;1233test_corpus5678&#34; already exists!' in rv.data
    rh.delete("/storage/1233test_corpus5678", {"uid": os.environ["TESTUSER"]})

def test_corpus_settings(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rh.delete("/storage/1233test_corpus5678", {"uid": os.environ["TESTUSER"]})
    post_data = {
        "name": "1233test_corpus5678",
        "group": "group",
        "domain": "domain",
        "origin": "origin",
        "description": "description",
        "pdf_reader": "pdf_reader",
        "document_alignment": "document_alignment",
        "sentence_alignment": "sentence_alignment",
        "sentence_splitter": "sentence_splitter",
        "autoalignment": "on"
    }
    rv = client.post('/create_corpus', data=post_data, follow_redirects=True)
    rv = client.get('/corpus_settings/1233test_corpus5678')
    assert b'Corpus Settings' in rv.data
    xml_metadata = rh.get("/metadata/1233test_corpus5678/"+os.environ["TESTUSER"], {"uid": os.environ["TESTUSER"]})
    parser = xml_parser.XmlParser(xml_metadata.split("\n"))
    metadata = parser.getMetadata()
    field_dict = opusrepository.initialize_field_dict()
    for key in post_data.keys():
        if key != "name":
            assert post_data[key] == metadata[field_dict[key][0]]

    post_data = {
        "name": "1233test_corpus5678",
        "group": "group2",
        "domain": "domain2",
        "origin": "origin2",
        "description": "description2",
        "pdf_reader": "pdf_reader2",
        "document_alignment": "document_alignment2",
        "sentence_alignment": "sentence_alignment2",
        "sentence_splitter": "sentence_splitter2",
        "autoalignment": "off"
    }
    rv = client.post('/corpus_settings/1233test_corpus5678', data=post_data, follow_redirects=True)
    xml_metadata = rh.get("/metadata/1233test_corpus5678/"+os.environ["TESTUSER"], {"uid": os.environ["TESTUSER"]})
    parser = xml_parser.XmlParser(xml_metadata.split("\n"))
    metadata = parser.getMetadata()
    field_dict = opusrepository.initialize_field_dict()
    for key in post_data.keys():
        if key != "name":
            assert post_data[key] == metadata[field_dict[key][0]]

    rh.delete("/storage/1233test_corpus5678", {"uid": os.environ["TESTUSER"]})

def test_remove_corpus(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rh.delete("/storage/1233test_corpus5678", {"uid": os.environ["TESTUSER"]})
    post_data = {
        "name": "1233test_corpus5678",
        "group": "group",
        "domain": "domain",
        "origin": "origin",
        "description": "description",
        "pdf_reader": "pdf_reader",
        "document_alignment": "document_alignment",
        "sentence_alignment": "sentence_alignment",
        "sentence_splitter": "sentence_splitter",
        "autoalignment": "on"
    }
    rv = client.post('/create_corpus', data=post_data, follow_redirects=True)
    xml_data = rh.get("/storage/1233test_corpus5678/"+os.environ["TESTUSER"], {"uid": os.environ["TESTUSER"]})
    assert '<list path="/1233test_corpus5678/'+os.environ["TESTUSER"]+'">' in xml_data
    rv = client.get('/remove_corpus?tobedeleted=1233test_corpus5678')
    xml_data = rh.get("/storage/1233test_corpus5678/"+os.environ["TESTUSER"], {"uid": os.environ["TESTUSER"]})
    assert 'Cannot find/read branch '+os.environ["TESTUSER"] in xml_data

    rh.delete("/storage/1233test_corpus5678", {"uid": os.environ["TESTUSER"]})

def test_create_group(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rh.delete("/group/1234test_group5678", {"uid": os.environ["TESTUSER"]})
    rv = client.get('/create_group')
    assert b'Create group' in rv.data
    post_data = {
        "name": "1234test_group5678",
        "members": "mikkotest2,mikkotest5,"
    }
    rv = client.post('/create_group', data=post_data, follow_redirects=True)
    assert b'Group &#34;1234test_group5678&#34; created!' in rv.data
    rv = client.post('/create_group', data=post_data, follow_redirects=True)
    assert b'Group &#34;1234test_group5678&#34; already exists!' in rv.data
    rh.delete("/group/1234test_group5678", {"uid": os.environ["TESTUSER"]})

def test_get_group_members(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rh.delete("/group/1234test_group5678", {"uid": os.environ["TESTUSER"]})
    post_data = {
        "name": "1234test_group5678",
        "members": "mikkotest2,mikkotest5,"
    }
    rv = client.post('/create_group', data=post_data, follow_redirects=True)
    members = opusrepository.get_group_members("1234test_group5678", os.environ["TESTUSER"])
    assert members[0] == "mikkotest2" and members[1] == "mikkotest5"

    rh.delete("/group/1234test_group5678", {"uid": os.environ["TESTUSER"]})

def test_edit_group(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rh.delete("/group/1234test_group5678", {"uid": os.environ["TESTUSER"]})
    post_data = {
        "name": "1234test_group5678",
        "members": "mikkotest2,mikkotest5,"
    }
    rv = client.post('/create_group', data=post_data, follow_redirects=True)
    members = opusrepository.get_group_members("1234test_group5678", os.environ["TESTUSER"])
    assert members[0] == "mikkotest2" and members[1] == "mikkotest5"
    post_data["members"] = "mikkotest5,"
    rv = client.post('/edit_group/1234test_group5678', data=post_data, follow_redirects=True)
    members = opusrepository.get_group_members("1234test_group5678", os.environ["TESTUSER"])
    assert b'Changes saved!' in rv.data
    assert len(members) == 1, members[0] == "mikkotest5"

    rh.delete("/group/1234test_group5678", {"uid": os.environ["TESTUSER"]})
    
def test_remove_group(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rh.delete("/group/1234test_group5678", {"uid": os.environ["TESTUSER"]})
    post_data = {
        "name": "1234test_group5678",
        "members": "mikkotest2,mikkotest5,"
    }
    rv = client.post('/create_group', data=post_data, follow_redirects=True)
    assert b'Group &#34;1234test_group5678&#34; created!' in rv.data
    rv = client.get('/remove_group?tobedeleted=1234test_group5678')
    xml_data = rh.get("/group/1234test_group5678", {"uid": os.environ["TESTUSER"]})
    assert "Group '1234test_group5678' not found" in xml_data

    rh.delete("/group/1234test_group5678", {"uid": os.environ["TESTUSER"]})

def test_show_corpus(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rh.post("/storage/1234_test_corpus_5678/"+os.environ["TESTUSER"], {"uid": os.environ["TESTUSER"]})
    rv = client.get('/show_corpus/1234_test_corpus_5678')
    for item in [b'1234_test_corpus_5678', b'uploads', b'monolingual', b'parallel']:
        assert item in rv.data
    assert b'clone' not in rv.data
    rh.delete("/storage/1234_test_corpus_5678/", {"uid": os.environ["TESTUSER"]})
    rv = client.get('/show_corpus/anonymous')
    assert b'clone' in rv.data

def test_download_file(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get('/download_file?path=%2Fmikkocorpus%2Fmikkotest%2Fxml%2Fen%2Dfi%2Fhtml%2Fajokielto%2Exml&filename=ajokielto%2Exml')
    assert b'fromDoc="en/html/ajokielto.xml" toDoc="fi/html/ajokielto.xml"' in rv.data

def test_clone_branch(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get('/clone_branch?corpusname=anonymous&branchclone=anonymous')
    assert b'Copied branch &#34;anonymous/anonymous&#34; to &#34;anonymous/' + os.environ["TESTUSER"].encode() in rv.data
    rh.delete("/storage/anonymous/" + os.environ["TESTUSER"], {"uid": os.environ["TESTUSER"]})

def test_search(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get('/search?corpusname=anonymous')
    assert b'{\n  "result": [\n    "anonymous"\n  ]\n}\n' in rv.data
    rv = client.get('/search?corpusname=mikko')
    assert b'{\n  "result": [\n    "mikkocorpus", \n    "mikkocorpus2", \n    "mikkocorpus3", \n    "mikkocorpus4"\n  ]\n}\n' in rv.data

def test_update_metadata(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    xml_data = rh.get("/metadata/mikkocorpus/mikkotest/uploads/html.tar.gz", {"uid": os.environ["TESTUSER"]})
    assert "<testkey>testvalue</testkey>" not in xml_data
    rv = client.get('/update_metadata?path=/mikkocorpus/mikkotest/uploads/html.tar.gz&changes={"testkey":"testvalue"}')
    assert b'Created/Overwrote meta data entry' in rv.data
    xml_data = rh.get("/metadata/mikkocorpus/mikkotest/uploads/html.tar.gz", {"uid": os.environ["TESTUSER"]})
    assert "<testkey>testvalue</testkey>" in xml_data
    rv = client.get('/update_metadata?path=/mikkocorpus/mikkotest/uploads/html.tar.gz&changes={"testkey":""}')
    xml_data = rh.get("/metadata/mikkocorpus/mikkotest/uploads/html.tar.gz", {"uid": os.environ["TESTUSER"]})
    assert "<testkey>testvalue</testkey>" not in xml_data

def test_edit_alignment(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get('/edit_alignment?path=/mikkocorpus/mikkotest/xml/en-fi/html/ajokielto.xml')
    assert b'ISA available at http://vm0081.kaj.pouta.csc.fi/isa/mikkotest/mikkocorpus' in rv.data

def test_get_branch(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get("/get_branch?branch=mikkotest&corpusname=mikkocorpus")
    for item in [b'monolingual', b'en', b'fi', b'parallel', b'en-fi', b'uploads', b'html.tar.gz']:
        assert item in rv.data

def test_get_subdirs(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get("/get_subdirs?branch=mikkotest&corpusname=mikkocorpus&subdir=/uploads")
    assert b'"html.tar.gz", \n      "file"' in rv.data
    rv = client.get("/get_subdirs?branch=mikkotest&corpusname=mikkocorpus&subdir=/monolingual")
    assert b'"en-fi", \n      "dir"' in rv.data

def test_upload_file(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])

    post_data = { "path": "/mikkocorpus/"+os.environ["TESTUSER"]+"/uploads/testfile.txt", "description": "" }
    post_data["file"] = (io.BytesIO(b'content'), 'testfile.txt')
    rv = client.post("/upload_file", data=post_data, follow_redirects=True, content_type='multipart/form-data')
    assert b'File &#34;/mikkocorpus/'+os.environ["TESTUSER"].encode()+b'/uploads/testfile.txt&#34; already exists' in rv.data
    rh.delete("/storage/mikkocorpus/"+os.environ["TESTUSER"]+"/uploads/testfile.txt", {"uid": os.environ["TESTUSER"]})

    rv = client.get("/upload_file?corpus=mikkocorpus&branch=mikkotest")
    assert b'Upload file' in rv.data
    post_data = { "path": "" }
    rv= client.post("/upload_file", data=post_data, follow_redirects=True)
    assert b'Invalid upload path' in rv.data
    post_data["path"] = "/mikkocorpus/testbranch/uploads//"
    rv = client.post("/upload_file", data=post_data, follow_redirects=True)
    assert b'Invalid branch name' in rv.data
    post_data["path"] = "/mikkocorpus/"+os.environ["TESTUSER"]+"/uploads//"
    post_data["description"] = ""
    rv = client.post("/upload_file", data=post_data, follow_redirects=True)
    assert b'No file part' in rv.data
    post_data["path"] = "/mikkocorpus/"+os.environ["TESTUSER"]+"/uploads/testfile.txt"
    post_data["file"] = (io.BytesIO(b'content'), '')
    rv = client.post("/upload_file", data=post_data, follow_redirects=True, content_type='multipart/form-data')
    assert b'No file part' in rv.data
    post_data["file"] = (io.BytesIO(b'content'), 'testfile.txt')
    rv = client.post("/upload_file", data=post_data, follow_redirects=True, content_type='multipart/form-data')
    assert b'Uploaded file &#34;testfile.txt&#34; to &#34;/mikkocorpus/'+os.environ["TESTUSER"].encode()+b'/uploads/testfile.txt&#34;' in rv.data
    post_data["file"] = (io.BytesIO(b'content'), 'testfile.exe')
    rv = client.post("/upload_file", data=post_data, follow_redirects=True, content_type='multipart/form-data')
    assert b'File format is not allowed' in rv.data

