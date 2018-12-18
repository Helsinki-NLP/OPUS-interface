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
        '<entry id="testuser" kind="user info">\
            <member>testuser</member>\
            <my_group>testuser</my_group>\
    </entry>'
    ))

    assert len(parser.elementList) == 0
    parser.recursiveGroups(ET.fromstring(
        '<entry id="testuser" kind="user info">\
            <member>testuser</member>\
            <member_of>testuser,public</member_of>\
            <my_group>testuser</my_group>\
        </entry>'
    ))
    assert parser.elementList[0] == "testuser" 
    assert parser.elementList[1] == "public"

def test_groupsForUser():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="group/testuser">',
                '<entry id="testuser" kind="user info">',
                    '<member>testuser</member>',
                    '<member_of>testuser,public</member_of>',
                    '<my_group>testuser</my_group>',
                '</entry>',
            '</list>',
            '<status code="0" location="/group/testuser/" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    groups = parser.groupsForUser()
    assert groups[0] == "testuser" 
    assert groups[1] == "public"

def test_recursiveCorpora():
    parser = xml_parser.XmlParser([])

    parser.recursiveCorpora(ET.fromstring(
        '<list path="">'\
            '<entry directory="testcorpus2/testuser" />'\
        '</list>'
    ))
    assert len(parser.elementList) == 0

    parser.recursiveCorpora(ET.fromstring(
        '<list path="">'\
            '<entry path="testcorpus/testuser" />'\
            '<entry path="testcorpus2/testuser" />'\
        '</list>'
    ))
    assert parser.elementList[0] == "testcorpus" 
    assert parser.elementList[1] == "testcorpus2"

    parser.recursiveCorpora(ET.fromstring(
        '<list path="">'\
            '<entry path="testcorpus/testuser" />'\
            '<entry path="testcorpus2/testuser" />'\
        '</list>'
    ))
    assert len(parser.elementList) == 2 
    assert parser.elementList[0] == "testcorpus" 
    assert parser.elementList[1] == "testcorpus2"
      
def test_corporaForUser():
    xml_data = [
        '<letsmt-ws version="56">'\
            '<list path="">'\
                '<entry path="testcorpus2/testuser" />'\
                '<entry path="testcorpus/testuser" />'\
            '</list>'\
            '<status code="0" location="/metadata" operation="GET" type="ok">Found 2 matching entries</status>'\
        '</letsmt-ws>'
    ]

    parser = xml_parser.XmlParser(xml_data)
    corpora = parser.corporaForUser()

    assert corpora[0] == "testcorpus2" 
    assert corpora[1] == "testcorpus"

def test_recursiveCollect():
    element = ET.fromstring(
        '<list path="/testcorpus">'\
            '<entry kind="branch" path="/testcorpus/testuser">'\
                '<name>testuser</name>'\
                '<group>public</group>'\
                '<owner>testuser</owner>'\
            '</entry>'\
        '</list>'
    )
    parser = xml_parser.XmlParser([])
    parser.recursiveCollect(element, "name")
    assert parser.elementList[-1] == "testuser"
    parser.recursiveCollect(element, "group")
    assert parser.elementList[-1] == "public"

def test_collectToList():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/testcorpus">',
                '<entry kind="branch" path="/testcorpus/testuser">',
                    '<name>testuser</name>',
                    '<group>public</group>',
                    '<owner>testuser</owner>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/testcorpus" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ] 

    parser = xml_parser.XmlParser(xml_data)
    elementlist = parser.collectToList("group")
    assert len(elementlist) == 1 
    assert elementlist[0] == "public"

def test_branchesForCorpus():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/testcorpus">',
                '<entry kind="branch" path="/testcorpus/testuser">',
                    '<name>testuser</name>',
                    '<group>public</group>',
                    '<owner>testuser</owner>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/testcorpus" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ] 

    parser = xml_parser.XmlParser(xml_data)
    branches = parser.branchesForCorpus()
    assert len(branches) == 1 
    assert branches[0] == "testuser"

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
            '<list path="/testcorpus/testuser/uploads">',
                '<entry kind="file">',
                    '<name>html.tar.gz</name>',
                    '<commit revision="HEAD">',
                        '<author>testuser</author>',
                        '<date>unknown</date>',
                    '</commit>',
                    '<group>public</group>',
                    '<owner>testuser</owner>',
                    '<size>14210</size>',
                '</entry>',
                '<entry kind="dir">',
                      '<name>html</name>',
                      '<commit revision="HEAD">',
                          '<author>testuser</author>',
                          '<date>unknown</date>',
                      '</commit>',
                      '<group>public</group>',
                      '<owner>testuser</owner>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/testcorpus/testuser/uploads" operation="GET" type="ok"></status>',
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
                '<entry path="testcorpus/testuser">',
                    '<name>testuser</name>',
                    '<gid>public</gid>',
                    '<import_queue></import_queue>',
                    '<langs>fi,en,sv</langs>',
                    '<modif>2018-11-27 14:05:14</modif>',
                    '<origin></origin>',
                    '<owner>testuser</owner>',
                    '<parallel-langs>fi-sv,en-fi,en-sv</parallel-langs>',
                '</entry>',
            '</list>',
            '<status code="0" location="/metadata/testcorpus/testuser" operation="GET"\
            type="ok">Found matching path ID. Listing all of its properties</status>',
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
        '<entry path="testcorpus/testuser/uploads/html.tar.gz">'\
              '<description>test</description>'\
              '<direction>unknown</direction>'\
              '<gid>public</gid>'\
              '<owner>testuser</owner>'\
              '<status>job canceled</status>'\
        '</entry>'
    )

    parser = xml_parser.XmlParser([])
    parser.recursiveMetadata(element)
    correct = {
        "description": "test",
        "direction": "unknown",
        "gid": "public",
        "owner": "testuser",
        "status": "job canceled"
    }
    for key in correct.keys():
        assert parser.elementDict[key] == correct[key]

def test_getMetadata():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="">',
            '<entry path="testcorpus/testuser/uploads/html.tar.gz">',
                  '<description>test</description>',
                  '<direction>unknown</direction>',
                  '<gid>public</gid>',
                  '<owner>testuser</owner>',
                  '<status>job canceled</status>',
            '</entry>',
            '</list>',
            '<status code="0" location="/metadata/testcorpus/testuser/uploads/html.tar.gz"\
            operation="GET" type="ok">Found matching path ID. Listing all of its properties</status>',
        '</letsmt-ws>'
    ]

    parser = xml_parser.XmlParser(xml_data)
    metadata = parser.getMetadata()
    correct = {
        "description": "test",
        "direction": "unknown",
        "gid": "public",
        "owner": "testuser",
        "status": "job canceled"
    }
    for key in correct.keys():
        assert metadata[key] == correct[key]

def test_getAlignmentCandidates():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="testcorpus/testuser/">',
                '<entry path="testcorpus/testuser/xml/en/html/ajokielto.xml">',
                    '<align-candidates>xml/fi/html/ajokielto.xml</align-candidates>',
                    '<aligned_with>xml/fi/html/ajokielto.xml,xml/sv/html/ajokielto.xml</aligned_with>',
                    '<gid>public</gid>',
                    '<imported_from>uploads/html.tar.gz:html/en/ajokielto.html</imported_from>',
                    '<language>en</language>',
                    '<owner>testuser</owner>',
                    '<parsed>ud/en/html/ajokielto.xml</parsed>',
                    '<resource-type>corpusfile</resource-type>',
                    '<size>38</size>',
                    '<status>successfully aligned with testcorpus/testuser/xml/sv/html/ajokielto.xml</status>',
                '</entry>',
            '</list>',
            '<status code="0" location="/metadata/testcorpus/testuser" operation="GET" type="ok">Found 1 matching\
            entries</status>',
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
            '<entry id="testuser" kind="group" owner="testuser" testattr="testvalue">'\
                '<user>testuser</user>'\
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
                '<entry id="testuser" kind="group" owner="testuser" testattr="testvalue">',
                    '<user>testuser</user>',
                '</entry>',
            '</list>',
            '<status code="0" location="/group/testuser" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    assert parser.getAttrFromTag("entry", "testattr") == "testvalue"

def test_getGroupOwner():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/group/">',
                '<entry id="testuser" kind="group" owner="testuser" testattr="testvalue">',
                    '<user>testuser</user>',
                '</entry>',
            '</list>',
            '<status code="0" location="/group/testuser" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    assert parser.getGroupOwner() == "testuser"

def test_getJobs():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="jobs">',
                '<entry name="job_1543831841_642742498" file="testcorpus/testuser/uploads/html.tar.gz"\
                id="890" job="testcorpus/testuser/jobs/import/uploads/html.tar.gz.xml" status="RUNNING" />',
            '</list>',
            '<status code="0" location="job" operation="GET" type="ok" />',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    jobs = parser.getJobs()
    assert jobs[0][0] == "testcorpus/testuser/uploads/html.tar.gz"
    assert jobs[0][1] == "RUNNING"
    
def test_getFileContent():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/testcorpus/testuser/xml/en/html/ajokielto.xml">',
                '<entry><?xml version="1.0" encoding="utf-8"?>',
                '<letsmt version="1.0">',
                '<p id="1">',
                '<s id="1">If a person is sentenced to a punishment for causing a serious traffic hazard, '+\
                'driving while intoxicated or driving while seriously intoxicated, the court also imposes a '+\
                'driving ban for at most five years.</s>',
                '</p>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/testcorpus/testuser/xml/en/html/ajokielto.xml"'+\
            'operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    content = parser.getFileContent()

    correct = '<?xml version="1.0" encoding="utf-8"?>\n'\
                  '<letsmt version="1.0">\n'\
                  '<p id="1">\n'\
                  '<s id="1">If a person is sentenced to a punishment for causing a serious traffic '+\
                  'hazard, driving while intoxicated or driving while seriously intoxicated, the court '+\
                  'also imposes a driving ban for at most five years.</s>\n'\
                  '</p>\n'
    print(content)
    print(correct)
    assert content == correct

def test_itemExists():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/testcorpus">',
                '<entry kind="branch" path="/testcorpus/testuser">',
                    '<name>testuser</name>',
                    '<group>public</group>',
                    '<owner>testuser</owner>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/testcorpus" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    
    assert parser.itemExists() == True
        
    xml_data = [
        '<letsmt-ws version="56">',
            '''<status code="6" location="/storage/testcorpusdoesnotexist" operation="GET"\
            type="error">Cannot find/read slot 'testcorpusdoesnotexist'</status>''',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)

    assert parser.itemExists() == False
    
def test_rh_get_storage():
    response = rh.get("/storage/1324_testcorpus_5768/"+os.environ["TESTUSER"], {"uid": os.environ["TESTUSER"]})
    texts = [
        '<letsmt-ws version="56">',
        '<list path="/1324_testcorpus_5768/'+os.environ["TESTUSER"]+'">',
        '<name>uploads</name>',
        '<name>xml</name>',
        '<status code="0" location="/storage/1324_testcorpus_5768/'+os.environ["TESTUSER"]+'" operation="GET" '+\
        'type="ok"></status>'
    ]
    for text in texts:
        assert text in response

def test_rh_get_download():
    response = rh.get(
        "/storage/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/xml/en/ajokielto.xml", 
        {"uid": os.environ["TESTUSER"], "action": "download", "archive": "0"}
    )
    print(response)
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
    response = rh.get(
        "/storage/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/xml/en/html/ajokielto.xml", 
        {"uid": os.environ["TESTUSER"], "action": "cat", "to": "1"}
    )
    assert len(response.split("\n")) == 9
    response = rh.get(
        "/storage/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/xml/en/html/ajokielto.xml", 
        {"uid": os.environ["TESTUSER"], "action": "cat", "to": "5"}
    )
    assert len(response.split("\n")) == 13
    assert '<s id="1">If a person is sentenced to a punishment for causing a serious traffic\
        hazard, driving while intoxicated or driving while seriously intoxicated, the court\
        also imposes a driving ban for at most five years.</s>' in response

def test_rh_post():
    rh.post(
        "/metadata/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/xml/en/html/ajokielto.xml", 
        {"uid": os.environ["TESTUSER"], "testkey": "testvalue"}
    )
    xml_metadata = rh.get(
        "/metadata/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/xml/en/html/ajokielto.xml", 
        {"uid": os.environ["TESTUSER"]}
    )
    parser = xml_parser.XmlParser(xml_metadata.split("\n"))
    metadata = parser.getMetadata()
    assert metadata["testkey"] == "testvalue"
    rh.post(
        "/metadata/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/xml/en/html/ajokielto.xml", 
        {"uid": os.environ["TESTUSER"], "testkey": "testvalue2"}
    )
    xml_metadata = rh.get(
        "/metadata/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/xml/en/html/ajokielto.xml", 
        {"uid": os.environ["TESTUSER"]}
    )
    parser = xml_parser.XmlParser(xml_metadata.split("\n"))
    metadata = parser.getMetadata()
    assert metadata["testkey"] == "testvalue2"

def test_rh_put():
    rh.post(
        "/metadata/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/xml/en/html/ajokielto.xml", 
        {"uid": os.environ["TESTUSER"], "testkey": "testvalue"}
    )
    xml_metadata = rh.get(
        "/metadata/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/xml/en/html/ajokielto.xml", 
        {"uid": os.environ["TESTUSER"]}
    )
    parser = xml_parser.XmlParser(xml_metadata.split("\n"))
    metadata = parser.getMetadata()
    assert metadata["testkey"] == "testvalue"
    rh.put(
        "/metadata/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/xml/en/html/ajokielto.xml", 
        {"uid": os.environ["TESTUSER"], "testkey": "testvalue2"}
    )
    xml_metadata = rh.get(
        "/metadata/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/xml/en/html/ajokielto.xml", 
        {"uid": os.environ["TESTUSER"]}
    )
    parser = xml_parser.XmlParser(xml_metadata.split("\n"))
    metadata = parser.getMetadata()
    assert "testvalue" in metadata["testkey"] and "testvalue2" in metadata["testkey"]

def test_rh_upload_and_delete():
    response = rh.upload(
        "/storage/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/uploads/test/test.txt", 
        {"uid": os.environ["TESTUSER"]}, opusrepository.UPLOAD_FOLDER+"/test.txt"
    )
    assert '<status code="0" location="/storage/1324_testcorpus_5768/'+os.environ["TESTUSER"]+\
        '/uploads/test/test.txt" operation="PUT" type="ok">update ok /1324_testcorpus_5768/'+\
        os.environ["TESTUSER"]+'/uploads/test/test.txt</status>' in response
    response = rh.get(
        "/storage/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/uploads/test/test.txt", 
        {"uid": os.environ["TESTUSER"]}
    )
    assert '<name>test.txt</name>' in response 
    response = rh.delete(
        "/storage/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/uploads/test/test.txt", 
        {"uid": os.environ["TESTUSER"]}
    )
    assert '<status code="0" location="/storage/1324_testcorpus_5768/'+os.environ["TESTUSER"]+\
        '/uploads/test/test.txt" operation="DELETE" type="ok">Deleted /storage/1324_testcorpus_5768/'+\
        os.environ["TESTUSER"]+'/uploads/test/test.txt</status>' in response
    response = rh.get(
        "/storage/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/uploads/test/test.txt", 
        {"uid": os.environ["TESTUSER"]}
    )
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
    assert opusrepository.get_group_owner(os.environ["TESTUSER"], os.environ["TESTUSER"]) == os.environ["TESTUSER"]

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
        "members": "testuser2,testuser5,"
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
        "members": "testuser2,testuser5,"
    }
    rv = client.post('/create_group', data=post_data, follow_redirects=True)
    members = opusrepository.get_group_members("1234test_group5678", os.environ["TESTUSER"])
    assert members[0] == "testuser2" and members[1] == "testuser5"

    rh.delete("/group/1234test_group5678", {"uid": os.environ["TESTUSER"]})

def test_edit_group(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rh.delete("/group/1234test_group5678", {"uid": os.environ["TESTUSER"]})
    post_data = {
        "name": "1234test_group5678",
        "members": "testuser2,testuser5,"
    }
    rv = client.post('/create_group', data=post_data, follow_redirects=True)
    members = opusrepository.get_group_members("1234test_group5678", os.environ["TESTUSER"])
    assert members[0] == "testuser2" and members[1] == "testuser5"
    post_data["members"] = "testuser5,"
    rv = client.post('/edit_group/1234test_group5678', data=post_data, follow_redirects=True)
    members = opusrepository.get_group_members("1234test_group5678", os.environ["TESTUSER"])
    assert b'Changes saved!' in rv.data
    assert len(members) == 1, members[0] == "testuser5"

    rh.delete("/group/1234test_group5678", {"uid": os.environ["TESTUSER"]})
    
def test_remove_group(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rh.delete("/group/1234test_group5678", {"uid": os.environ["TESTUSER"]})
    post_data = {
        "name": "1234test_group5678",
        "members": "testuser2,testuser5,"
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
    rv = client.get('/download_file?path=%2F1324_testcorpus_5768%2F'+os.environ["TESTUSER"]+\
        '%2Fxml%2Fen%2Dfi%2Fhtml%2Fajokielto%2Exml&filename=ajokielto%2Exml')
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
    rv = client.get('/search?corpusname=1324')
    assert b'{\n  "result": [\n    "1324_testcorpus_5768", \n    "1324_testcorpus_57682", '+\
        b'\n    "1324_testcorpus_57683", \n    "1324_testcorpus_57684"\n  ]\n}\n' in rv.data

def test_update_metadata(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    xml_data = rh.get(
        "/metadata/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/uploads/html.tar.gz", 
        {"uid": os.environ["TESTUSER"]}
    )
    assert "<testkey>testvalue</testkey>" not in xml_data
    rv = client.get('/update_metadata?path=/1324_testcorpus_5768/'+os.environ["TESTUSER"]+\
        '/uploads/html.tar.gz&changes={"testkey":"testvalue"}')
    assert b'Created/Overwrote meta data entry' in rv.data
    xml_data = rh.get(
        "/metadata/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/uploads/html.tar.gz", 
        {"uid": os.environ["TESTUSER"]}
    )
    assert "<testkey>testvalue</testkey>" in xml_data
    rv = client.get('/update_metadata?path=/1324_testcorpus_5768/'+os.environ["TESTUSER"]+\
        '/uploads/html.tar.gz&changes={"testkey":""}')
    xml_data = rh.get(
        "/metadata/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/uploads/html.tar.gz", 
        {"uid": os.environ["TESTUSER"]}
    )
    assert "<testkey>testvalue</testkey>" not in xml_data

def test_edit_alignment(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get('/edit_alignment?path=/1324_testcorpus_5768/'+os.environ["TESTUSER"]+'/xml/en-fi/html/ajokielto.xml')
    assert b'ISA available at http://vm0081.kaj.pouta.csc.fi/isa/'+\
        os.environ["TESTUSER"].encode()+b'/1324_testcorpus_5768' in rv.data

def test_get_branch(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get("/get_branch?branch="+os.environ["TESTUSER"]+"&corpusname=1324_testcorpus_5768")
    for item in [b'monolingual', b'en', b'fi', b'parallel', b'en-fi', b'uploads', b'html.tar.gz']:
        assert item in rv.data

def test_get_subdirs(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get("/get_subdirs?branch="+os.environ["TESTUSER"]+"&corpusname=1324_testcorpus_5768&subdir=/uploads")
    assert b'"html.tar.gz", \n      "file"' in rv.data
    rv = client.get("/get_subdirs?branch="+os.environ["TESTUSER"]+"&corpusname=1324_testcorpus_5768&subdir=/monolingual")
    assert b'"en-fi", \n      "dir"' in rv.data

def test_upload_file(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])

    post_data = { "path": "/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/uploads/testfile.txt", "description": "" }
    post_data["file"] = (io.BytesIO(b'content'), 'testfile.txt')
    rv = client.post("/upload_file", data=post_data, follow_redirects=True, content_type='multipart/form-data')
    assert b'File &#34;/1324_testcorpus_5768/'+os.environ["TESTUSER"].encode()+\
        b'/uploads/testfile.txt&#34; already exists' in rv.data
    rh.delete(
        "/storage/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/uploads/testfile.txt", 
        {"uid": os.environ["TESTUSER"]}
    )

    rv = client.get("/upload_file?corpus=1324_testcorpus_5768&branch="+os.environ["TESTUSER"])
    assert b'Upload file' in rv.data
    post_data = { "path": "" }
    rv= client.post("/upload_file", data=post_data, follow_redirects=True)
    assert b'Invalid upload path' in rv.data
    post_data["path"] = "/1324_testcorpus_5768/testbranch/uploads//"
    rv = client.post("/upload_file", data=post_data, follow_redirects=True)
    assert b'Invalid branch name' in rv.data
    post_data["path"] = "/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/uploads//"
    post_data["description"] = ""
    rv = client.post("/upload_file", data=post_data, follow_redirects=True)
    assert b'No file part' in rv.data
    post_data["path"] = "/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/uploads/testfile.txt"
    post_data["file"] = (io.BytesIO(b'content'), '')
    rv = client.post("/upload_file", data=post_data, follow_redirects=True, content_type='multipart/form-data')
    assert b'No file part' in rv.data
    post_data["file"] = (io.BytesIO(b'content'), 'testfile.txt')
    rv = client.post("/upload_file", data=post_data, follow_redirects=True, content_type='multipart/form-data')
    assert b'Uploaded file &#34;testfile.txt&#34; to &#34;/1324_testcorpus_5768/'+\
        os.environ["TESTUSER"].encode()+b'/uploads/testfile.txt&#34;' in rv.data
    post_data["file"] = (io.BytesIO(b'content'), 'testfile.exe')
    rv = client.post("/upload_file", data=post_data, follow_redirects=True, content_type='multipart/form-data')
    assert b'File format is not allowed' in rv.data

def test_get_metadata(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get("/get_metadata?path=/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/uploads/html.tar.gz")
    for item in [b'"gid": "public"', b'"owner": "'+os.environ["TESTUSER"].encode()+\
        b'"', b'"username": "'+os.environ["TESTUSER"].encode()+b'"']:
        assert item in rv.data

def test_get_filecontent(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get("/get_filecontent?path=/1324_testcorpus_5768/"+os.environ["TESTUSER"]+"/xml/en-fi/html/ajokielto.xml")
    for item in [b'fromDoc=\\"en/html/ajokielto.xml\\" toDoc=\\"fi/html/ajokielto.xml\\"', b'</linkGrp>\\n</cesAlign>']:
        assert item in rv.data

def test_import_file(client):
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    username = os.environ["TESTUSER"]
    rv = client.get("/import_file?path=/1324_testcorpus_5768/"+username+"/uploads/html.tar.gz&command=import")
    assert b'<status code=\\"0\\" location=\\"/job/1324_testcorpus_5768/'+username.encode()+\
        b'/uploads/html.tar.gz\\" operation=\\"PUT\\" type=\\"ok\\">1</status>' in rv.data
    rv = client.get("/import_file?path=/1324_testcorpus_5768/"+username+"/uploads/html.tar.gz&command=import again")
    assert b'<status code=\\"0\\" location=\\"/job/1324_testcorpus_5768/'+username.encode()+\
        b'/uploads/html.tar.gz\\" operation=\\"PUT\\" type=\\"ok\\">1</status>' in rv.data
    rv = client.get("/import_file?path=/1324_testcorpus_5768/"+username+"/uploads/html.tar.gz&command=stop importing")
    assert b'operation=\\"DELETE\\" type=\\"ok\\">canceled job for 1324_testcorpus_5768/'+username.encode()+\
        b'/uploads/html.tar.gz 1324_testcorpus_5768/'+username.encode()+b'/jobs/import/uploads/html.tar.gz.xml' in rv.data
    rv = client.get("/import_file?path=/1324_testcorpus_5768/"+username+"/uploads/html.tar.gz&command=cancel import")
    assert b'operation=\\"DELETE\\" type=\\"ok\\">canceled job for 1324_testcorpus_5768/'+username.encode()+\
        b'/uploads/html.tar.gz 1324_testcorpus_5768/'+username.encode()+b'/jobs/import/uploads/html.tar.gz.xml' in rv.data

def test_delete_file(client):
    username = os.environ["TESTUSER"]
    login(client, username, os.environ["TESTPW"])
    assert True
