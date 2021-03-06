import xml.parsers.expat
import xml.etree.ElementTree as ET
import re
import html
from iso639 import languages

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

        self.elementDict = {}
        self.elementList = []
        self.elementString = ""

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

    def recursiveGroups(self, element):
        for child in element:
            if child.tag == "member_of" and child.text:
                self.elementList = child.text.split(",")
            self.recursiveGroups(child)

    def groupsForUser(self):
        root = ET.fromstring("\n".join(self.xmlData))
        self.recursiveGroups(root)

        return self.elementList

    def recursiveCorpora(self, element):
        for child in element:
            if element.tag == "list" and "path" in child.attrib.keys():
                m = re.search("^(.*)\/", child.attrib["path"])
                if m.group(1) not in self.elementList:
                    self.elementList.append(m.group(1))
            self.recursiveCorpora(child)

    def corporaForUser(self):
        root = ET.fromstring("\n".join(self.xmlData))
        self.recursiveCorpora(root)

        return self.elementList
            
    def recursiveCollect(self, element, tag):
        for child in element:
            if child.tag == tag:
                self.elementList.append(child.text)
            self.recursiveCollect(child, tag)

    def collectToList(self, tag):
        root = ET.fromstring("\n".join(self.xmlData))
        self.recursiveCollect(root, tag)

        return self.elementList

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
                dirs.append([self.chara, kind, self.chara])
                kind = ""
        return dirs
        
    def isoName(self, lan):
        try:
            return languages.get(alpha2=lan).name
        except:
            return lan

    def isoDirection(self, direc):
        langs = direc.split("-")
        return self.isoName(langs[0])+"-"+self.isoName(langs[1])

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
        monolingual = [[x, "dir", self.isoName(x)] for x in monolingual_pre]
        parallel = [[x, "dir", self.isoDirection(x)] for x in parallel_pre]
        return (monolingual, parallel)

    def recursiveMetadata(self, element):
        for child in element:
            if element.tag == "entry":
                if child.text:
                    self.elementDict[child.tag] = html.escape(child.text)
                else:
                    self.elementDict[child.tag] = ""
            self.recursiveMetadata(child)

    def getMetadata(self):
        root = ET.fromstring("\n".join(self.xmlData))
        self.recursiveMetadata(root)
        
        return self.elementDict

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

    def recursiveAttrTag(self, element, tag, attr):
        for child in element:
            if child.tag == tag:
                self.elementString = child.attrib[attr]
            self.recursiveAttrTag(child, tag, attr)

    def getAttrFromTag(self, tag, attr):
        root = ET.fromstring("\n".join(self.xmlData))
        self.recursiveAttrTag(root, tag, attr)

        return self.elementString

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
        parse = False
        content = ""
        for line in self.xmlData:
            line = line.strip()
            if line[:7] == "<entry>":
                parse = True
                line = line[7:]
            if line[-8:] == "</entry>":
                parse = False
                break
            if parse:
                content += line + "\n"
        return content

    def itemExists(self):
        for line in self.xmlData:
            self.parseLine(line)
            if self.start == "entry":
                return True
        return False

    def parseTMX(self):
        lang = ""
        curLang, line1, line2 = "", "", ""
        content = []
        for line in self.xmlData:
            self.parseLine(line)
            if self.start == "tuv":
                lang = self.attrs["xml:lang"]
                if curLang == "":
                    curLang = lang
            elif self.start == "seg":
                self.start = ""
                line = self.chara
                if lang == curLang:
                    line1 += line + " "
                else:
                    line2 += line + " "
            if self.end == "tu":
                self.end = ""
                content.append((line1.strip(), line2.strip()))
                line1, line2 = "", ""
        return content

    def parseDocXML(self):
        data = []
        for line in self.xmlData:
            self.parseLine(line)
            if self.start == "s":
                data.append(self.chara)
                self.start = ""
        return data
