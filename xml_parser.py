import xml.parsers.expat
import re
import html

class XmlParser:

    def __init__(self, xmlData):
        self.xmlData = xmlData
        self.start = ""
        self.attrs = {}
        self.chara = ""
        self.end = ""

        self.parser = xml.parsers.expat.ParserCreate()
        self.parser.StartElementHandler = self.startElement
        self.parser.CharacterDataHandler = self.charData
        self.parser.EndElementHandler = self.endElement

    def startElement(self, name, attrs):
        self.start = name
        self.attrs = attrs

    def charData(self, data):
        self.chara = data

    def endElement(self, name):
        self.end = name

    def parseLine(self, line):
        self.parser.Parse(line)
        return('"'+self.start+'"', '"'+self.chara+'"', '"'+self.end+'"', self.attrs)
        
    def parse(self):
        for line in self.xmlData:
            print(self.parseLine(line))

    def groupsForUser(self):
        groups = []
        for line in self.xmlData:
            self.parseLine(line)
            if self.start == "member_of" and self.end == "member_of":
                groups = self.chara.split(",")
                break
        return groups

    def corporaForUser(self):
        corpora = []
        for line in self.xmlData:
            self.parseLine(line)
            if self.start == "entry" and self.end == "entry":
                m = re.search("^(.*)\/", self.attrs["path"])
                if m.group(1) not in corpora:
                    corpora.append(m.group(1))
        return corpora
            
    def collectToList(self, tag):
        result = []
        for line in self.xmlData:
            self.parseLine(line)
            if self.start == tag and self.end == tag:
                result.append(self.chara)
        return result

    def branchesForCorpus(self):
        return self.collectToList("name")

    def getUsers(self):
        return self.collectToList("user")

    def navigateDirectory(self):
        dirs = []
        entryFound = False
        kind = ""
        for line in self.xmlData:
            self.parseLine(line)
            if self.start == "entry":
                kind = self.attrs["kind"]
            if self.start == "name" and kind in ["dir", "file"]:
                dirs.append([self.chara, kind])
                kind = ""
        return dirs

    def getMonolingualAndParallel(self):
        monolingual_pre = []
        parallel_pre = []
        for line in self.xmlData:
            self.parseLine(line)
            if self.start == "langs":
                monolingual_pre = self.chara.split(",")
            elif self.start == "parallel-langs":
                parallel_pre = self.chara.split(",")
            if monolingual_pre != [] and parallel_pre != []:
                break
        monolingual = [[x, "dir"] for x in monolingual_pre]
        parallel = [[x, "dir"] for x in parallel_pre]
        return (monolingual, parallel)

    def getMetadata(self):
        metadata = {}
        storeValues = False
        for line in self.xmlData:
            self.parseLine(line)
            if self.end == "entry":
                storeValues = False
            if storeValues and self.start != "":
                metadata[self.start] = self.chara
            if self.start == "entry":
                storeValues = True
                if "path" in self.attrs.keys():
                    metadata["path"] = self.attrs["path"]
        return metadata

    def getAlignCandidates(self):
        candidates = {}
        key = ""
        value = []
        for line in self.xmlData:
            self.parseLine(line)
            if self.start == "entry":
                m = re.search("^.*?/.*?/.*?/(.*)", self.attrs["path"])
                if m:
                    key = m.group(1)
                else:
                    key = ""
            if self.start == "align-candidates":
                value = re.sub("xml/", "", self.chara).split(",")
                candidates[key] = value
                key = ""
                value = []
        return candidates

    def getAttrFromTag(self, tag, attr):
        result = "unknown"
        for line in self.xmlData:
            self.parseLine(line)
            if self.start == tag:
                result = self.attrs[attr]
                break
        return result

    def getGroupOwner(self):
        return self.getAttrFromTag("entry", "owner")
        
    def getJobPath(self):
        return self.getAttrFromTag("entry", "path")

    def getJobs(self):
        info = []
        for line in self.xmlData:
            self.parseLine(line)
            if self.start == "entry" and self.end == "entry":
                info.append((self.attrs["file"], self.attrs["status"]))
        return info 

    def getFileContent(self):
        content = ""
        for line in self.xmlData:
            self.parseLine(line)
            if self.start == "entry":
                newcontent = html.unescape(line).strip()
                if newcontent[:7] == "<entry>":
                    newcontent = newcontent[7:]
                if newcontent[-8:] == "</entry>":
                    newcontent = newcontent[:-8]
                content += newcontent + "\n"
            if self.end == "entry":
                break
        return content

'''
xml_data = """
<letsmt-ws version="56">
    <list path="">
        <entry path="oikeus8/mikkotest/jobs/import/uploads/html.tar" />
    </list>
    <status code="0" location="/metadata" operation="GET" type="ok">Found 1 matching entries</status>
</letsmt-ws>
"""
           
parser = XmlParser(xml_data.split("\n"))
print(parser.getJobPath())
'''
