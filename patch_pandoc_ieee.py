import os
import zipfile
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

# Ensure PNG content type
if 'Extension="png"' not in types_xml:
    types_xml = types_xml.replace('</Types>', '<Default Extension="png" ContentType="image/png"/></Types>')

# Add relationships for 3 images
rels_to_add = """
  <Relationship Id="rIdImg1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
  <Relationship Id="rIdImg2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image2.png"/>
  <Relationship Id="rIdImg3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image3.png"/>
"""
rels_xml = rels_xml.replace('</Relationships>', rels_to_add + '</Relationships>')

def make_drawing_xml(r_id, doc_id, name, width_cx=3000000, height_cy=1700000):
    return f'''<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><wp:extent cx="{width_cx}" cy="{height_cy}"/><wp:docPr id="{doc_id}" name="{name}"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="0" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="{r_id}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{width_cx}" cy="{height_cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>'''

# Replace placeholders / insert figure images
fig1_drawing = f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr>{make_drawing_xml("rIdImg1", 1, "Fig1", 3000000, 1700000)}</w:p>'
fig2_drawing = f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr>{make_drawing_xml("rIdImg2", 2, "Fig2", 3000000, 1800000)}</w:p>'
fig3_drawing = f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr>{make_drawing_xml("rIdImg3", 3, "Fig3", 3000000, 1700000)}</w:p>'

doc_xml = re.sub(r'(<w:p[^>]*>.*?Figure 1: TokenShield container-level system architecture.*?</w:p>)', fig1_drawing + r'\1', doc_xml, flags=re.DOTALL)
doc_xml = re.sub(r'(<w:p[^>]*>.*?Figure 2: Eight-stage progressive mitigation pipeline.*?</w:p>)', fig2_drawing + r'\1', doc_xml, flags=re.DOTALL)
doc_xml = re.sub(r'(<w:p[^>]*>.*?Figure 3: Packet-level sequence for token-theft incident.*?</w:p>)', fig3_drawing + r'\1', doc_xml, flags=re.DOTALL)

# Insert 1-column section break before Introduction heading so Title/Abstract stay full width
intro_pos = doc_xml.find('Introduction')
if intro_pos != -1:
    p_before_intro = doc_xml.rfind('<w:p', 0, intro_pos)
    sect_1col = '''<w:p><w:pPr><w:sectPr><w:type w:val="continuous"/><w:cols w:num="1"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="900" w:bottom="1080" w:left="900" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:pPr></w:p>'''
    doc_xml = doc_xml[:p_before_intro] + sect_1col + doc_xml[p_before_intro:]

# Insert 2-column section break for entire paper body at end of document
sect_2col = '''<w:sectPr><w:type w:val="continuous"/><w:cols w:num="2" w:space="360" w:equal="1"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="900" w:bottom="1080" w:left="900" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'''
doc_xml = re.sub(r'<w:sectPr\s*/>', sect_2col, doc_xml)

files['word/document.xml'] = doc_xml.encode('utf-8')
files['word/_rels/document.xml.rels'] = rels_xml.encode('utf-8')
files['[Content_Types].xml'] = types_xml.encode('utf-8')

files['word/media/image1.png'] = img1_bytes
files['word/media/image2.png'] = img2_bytes
files['word/media/image3.png'] = img3_bytes

with zipfile.ZipFile(out_docx, 'w', zipfile.ZIP_DEFLATED) as zout:
    for name, content in files.items():
        zout.writestr(name, content)

print("Updated TokenShield_IEEE_Paper.docx with 2-column IEEE layout properties.")
