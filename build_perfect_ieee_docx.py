import os
import zipfile
import xml.etree.ElementTree as ET
import re

img_dir = "/Users/yashpachhade/tokenshield/diagrams"
with open(os.path.join(img_dir, "fig1_architecture.png"), "rb") as f:
    img1_bytes = f.read()
with open(os.path.join(img_dir, "fig2_mitigation.png"), "rb") as f:
    img2_bytes = f.read()
with open(os.path.join(img_dir, "fig3_sequence.png"), "rb") as f:
    img3_bytes = f.read()

src_docx = "/Users/yashpachhade/tokenshield/TokenShield_Pandoc.docx"
out_docx = "/Users/yashpachhade/tokenshield/TokenShield_IEEE_Paper.docx"

with zipfile.ZipFile(src_docx, 'r') as zin:
    files = {name: zin.read(name) for name in zin.namelist()}

doc_xml = files['word/document.xml'].decode('utf-8')
rels_xml = files['word/_rels/document.xml.rels'].decode('utf-8')
types_xml = files['[Content_Types].xml'].decode('utf-8')

# 1. Ensure PNG content type
if 'Extension="png"' not in types_xml:
    types_xml = types_xml.replace('</Types>', '<Default Extension="png" ContentType="image/png"/></Types>')

# 2. Add image relationships
rels_to_add = """
  <Relationship Id="rIdImg1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
  <Relationship Id="rIdImg2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image2.png"/>
  <Relationship Id="rIdImg3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image3.png"/>
"""
rels_xml = rels_xml.replace('</Relationships>', rels_to_add + '</Relationships>')

def make_drawing_xml(r_id, doc_id, name, width_cx=2800000, height_cy=1600000):
    return f'''<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><wp:extent cx="{width_cx}" cy="{height_cy}"/><wp:docPr id="{doc_id}" name="{name}"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="0" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="{r_id}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{width_cx}" cy="{height_cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>'''

# Insert figure images
fig1_drawing = f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr>{make_drawing_xml("rIdImg1", 1, "Fig1", 2800000, 1600000)}</w:p>'
fig2_drawing = f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr>{make_drawing_xml("rIdImg2", 2, "Fig2", 2800000, 1700000)}</w:p>'
fig3_drawing = f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr>{make_drawing_xml("rIdImg3", 3, "Fig3", 2800000, 1600000)}</w:p>'

doc_xml = re.sub(r'(<w:p[^>]*>.*?Figure 1: TokenShield container-level system architecture.*?</w:p>)', fig1_drawing + r'\1', doc_xml, flags=re.DOTALL)
doc_xml = re.sub(r'(<w:p[^>]*>.*?Figure 2: Eight-stage progressive mitigation pipeline.*?</w:p>)', fig2_drawing + r'\1', doc_xml, flags=re.DOTALL)
doc_xml = re.sub(r'(<w:p[^>]*>.*?Figure 3: Packet-level sequence for token-theft incident.*?</w:p>)', fig3_drawing + r'\1', doc_xml, flags=re.DOTALL)

# 3. Parse XML using ElementTree to place EXACT section properties
root = ET.fromstring(doc_xml)
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
body = root.find('w:body', ns)

paragraphs = body.findall('w:p', ns)

# Section 1 break (1 column for Title & Abstract header)
# We find P3 (keywords)
for p in paragraphs:
    texts = ''.join(t.text for t in p.findall('.//w:t', ns) if t.text)
    if 'framework-agnostic middleware' in texts or 'session hijacking' in texts:
        pPr = p.find('w:pPr', ns)
        if pPr is None:
            pPr = ET.SubElement(p, f'{{{ns["w"]}}}pPr')
        
        sectPr = ET.SubElement(pPr, f'{{{ns["w"]}}}sectPr')
        type_elem = ET.SubElement(sectPr, f'{{{ns["w"]}}}type')
        type_elem.set(f'{{{ns["w"]}}}val', 'continuous')
        cols_elem = ET.SubElement(sectPr, f'{{{ns["w"]}}}cols')
        cols_elem.set(f'{{{ns["w"]}}}num', '1')
        pgSz_elem = ET.SubElement(sectPr, f'{{{ns["w"]}}}pgSz')
        pgSz_elem.set(f'{{{ns["w"]}}}w', '12240')
        pgSz_elem.set(f'{{{ns["w"]}}}h', '15840')
        pgMar_elem = ET.SubElement(sectPr, f'{{{ns["w"]}}}pgMar')
        pgMar_elem.set(f'{{{ns["w"]}}}top', '1080')
        pgMar_elem.set(f'{{{ns["w"]}}}right', '900')
        pgMar_elem.set(f'{{{ns["w"]}}}bottom', '1080')
        pgMar_elem.set(f'{{{ns["w"]}}}left', '900')
        break

# Section 2 break (2 columns for body text)
# We remove any existing trailing sectPr and append new 2-column sectPr
for child in list(body):
    if child.tag == f'{{{ns["w"]}}}sectPr':
        body.remove(child)

sectPr2 = ET.SubElement(body, f'{{{ns["w"]}}}sectPr')
type_elem2 = ET.SubElement(sectPr2, f'{{{ns["w"]}}}type')
type_elem2.set(f'{{{ns["w"]}}}val', 'continuous')
cols_elem2 = ET.SubElement(sectPr2, f'{{{ns["w"]}}}cols')
cols_elem2.set(f'{{{ns["w"]}}}num', '2')
cols_elem2.set(f'{{{ns["w"]}}}space', '360')
cols_elem2.set(f'{{{ns["w"]}}}equal', '1')
pgSz_elem2 = ET.SubElement(sectPr2, f'{{{ns["w"]}}}pgSz')
pgSz_elem2.set(f'{{{ns["w"]}}}w', '12240')
pgSz_elem2.set(f'{{{ns["w"]}}}h', '15840')
pgMar_elem2 = ET.SubElement(sectPr2, f'{{{ns["w"]}}}pgMar')
pgMar_elem2.set(f'{{{ns["w"]}}}top', '1080')
pgMar_elem2.set(f'{{{ns["w"]}}}right', '900')
pgMar_elem2.set(f'{{{ns["w"]}}}bottom', '1080')
pgMar_elem2.set(f'{{{ns["w"]}}}left', '900')

ET.register_namespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')
ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
ET.register_namespace('wp', 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing')
ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
ET.register_namespace('pic', 'http://schemas.openxmlformats.org/drawingml/2006/picture')
ET.register_namespace('m', 'http://schemas.openxmlformats.org/officeDocument/2006/math')

new_doc_xml = ET.tostring(root, encoding='utf-8')

files['word/document.xml'] = new_doc_xml
files['word/_rels/document.xml.rels'] = rels_xml.encode('utf-8')
files['[Content_Types].xml'] = types_xml.encode('utf-8')

files['word/media/image1.png'] = img1_bytes
files['word/media/image2.png'] = img2_bytes
files['word/media/image3.png'] = img3_bytes

with zipfile.ZipFile(out_docx, 'w', zipfile.ZIP_DEFLATED) as zout:
    for name, content in files.items():
        zout.writestr(name, content)

print("Successfully created exact 2-column IEEE Word document at:", out_docx)
