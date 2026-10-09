"""Bounded, format-explicit text extraction and structure-aware chunking."""
from __future__ import annotations
import io, re, zipfile

MAX_BYTES = 5 * 1024 * 1024
MAX_CHUNK_CHARS = 1200
CHUNK_OVERLAP_CHARS = 160
PARSER_VERSION = "ingestion-v1"
CHUNKING_VERSION = "heading-paragraph-1200-overlap-160-v1"
SUPPORTED = {".txt", ".md", ".pdf", ".docx"}

def extract(filename: str, data: bytes):
 """Return ordered text segments with provenance; fail closed on unsupported/empty input."""
 suffix='.'+filename.rsplit('.',1)[-1].lower() if '.' in filename else ''
 if suffix not in SUPPORTED: raise ValueError(f"unsupported file type {suffix or '(none)'}; supported: .txt, .md, .pdf, .docx")
 if not data or len(data)>MAX_BYTES: raise ValueError('file must be non-empty and no larger than 5 MiB')
 if suffix in ('.txt','.md'):
  text=data.decode('utf-8-sig',errors='strict')
  return _text_segments(text)
 if suffix=='.pdf':
  from pypdf import PdfReader
  reader=PdfReader(io.BytesIO(data),strict=True)
  if len(reader.pages)>150: raise ValueError('PDF exceeds 150-page limit')
  segments=[]
  for n,page in enumerate(reader.pages,1):
   text=(page.extract_text() or '').strip()
   if text: segments.extend(_text_segments(text,section=f'Page {n}',location=f'page:{n}'))
  if not segments: raise ValueError('PDF contains no extractable text; scanned-image OCR is not supported')
  return segments
 # Reject zip bombs and malformed Office containers before invoking the parser.
 with zipfile.ZipFile(io.BytesIO(data)) as zf:
  infos=zf.infolist()
  if len(infos)>2000 or sum(i.file_size for i in infos)>40*1024*1024: raise ValueError('DOCX archive exceeds extraction limits')
  if any(i.file_size>0 and i.file_size/max(i.compress_size,1)>1000 for i in infos): raise ValueError('DOCX archive compression ratio exceeds limit')
  if 'word/document.xml' not in zf.namelist(): raise ValueError('invalid DOCX package')
 from docx import Document
 doc=Document(io.BytesIO(data)); segments=[]; headings=[]; pos=0
 for item in doc.iter_inner_content():
  if hasattr(item,'text'):
   text=item.text.strip()
   if not text: continue
   style=getattr(getattr(item,'style',None),'name','') or ''
   match=re.match(r'Heading\s+(\d+)',style,re.I)
   if match:
    level=max(1,min(6,int(match.group(1)))); headings=headings[:level-1]+[text]; continue
   segments.append({'text':text,'section':' > '.join(headings) or 'Document body','location':f'paragraph:{len(segments)+1}','start':pos,'end':pos+len(text)})
   pos+=len(text)+1
  elif hasattr(item,'rows'):
   rows=[' | '.join(cell.text.replace('\n',' ').strip() for cell in row.cells) for row in item.rows]
   text='\n'.join(rows).strip()
   if text: segments.append({'text':text,'section':' > '.join(headings+["Table"]) if headings else 'Table','location':f'table:{len(segments)+1}','start':pos,'end':pos+len(text)}); pos+=len(text)+1
 if not segments: raise ValueError('DOCX contains no extractable text')
 return segments

def _text_segments(text, section='', location=''):
 lines=text.replace('\r\n','\n').replace('\r','\n').split('\n'); headings=[]; segments=[]; pos=0; para=[]; para_start=0
 def flush(end):
  nonlocal para,para_start
  value=' '.join(x.strip() for x in para if x.strip()).strip()
  if value: segments.append({'text':value,'section':section or (' > '.join(headings) or 'Document body'),'location':location or f'char:{para_start}-{end}','start':para_start,'end':end})
  para=[]
 for line in lines:
  stripped=line.strip(); heading=re.match(r'^(#{1,6})\s+(.+)$',stripped)
  if heading:
   flush(pos); level=len(heading.group(1)); headings=headings[:level-1]+[heading.group(2).strip()]
  elif not stripped:
   flush(pos)
  else:
   if not para: para_start=pos
   para.append(stripped)
  pos+=len(line)+1
 flush(pos)
 if not segments: raise ValueError('document contains no extractable text')
 return segments

def chunk(segments, max_chars=MAX_CHUNK_CHARS, overlap=CHUNK_OVERLAP_CHARS):
 """Pack paragraphs under headings; oversized paragraphs split on word boundaries."""
 if not 300<=max_chars<=4000 or not 0<=overlap<max_chars//2: raise ValueError('invalid chunking bounds')
 chunks=[]; buf=[]; meta=None
 def emit():
  nonlocal buf,meta
  if not buf: return
  txt='\n\n'.join(x['text'] for x in buf).strip()
  chunks.append({'text':txt,'section':meta['section'],'location':'; '.join(dict.fromkeys(x['location'] for x in buf)),'start':min(x['start'] for x in buf),'end':max(x['end'] for x in buf)})
  if overlap:
   tail=txt[-overlap:]
   buf=[{'text':tail,'section':meta['section'],'location':meta['location'],'start':max(0,meta['end']-overlap),'end':meta['end']}]
  else: buf=[]
 for segment in segments:
  value=segment['text']; section=segment['section']
  pieces=[]
  while len(value)>max_chars:
   cut=value.rfind(' ',0,max_chars+1)
   if cut<max_chars//2: cut=max_chars
   pieces.append(value[:cut].strip()); value=value[max(1,cut-overlap):].strip()
  if value: pieces.append(value)
  for piece in pieces:
   item={**segment,'text':piece}
   if buf and meta['section']!=section:
    emit()
    # emit() retains overlap, but overlap must never cross a section boundary.
    buf=[]
    meta=segment
   elif buf and sum(len(x['text']) for x in buf)+len(piece)+2>max_chars: emit()
   if not buf: meta=segment
   if sum(len(x['text']) for x in buf)+len(piece)+2>max_chars: buf=[]
   buf.append(item)
 emit()
 return chunks
