"""Natural Earth public-domain land outlines, equirectangular, no political borders."""
import json
from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=1)
def land():
    data=json.loads((Path(__file__).parent/'data'/'ne_110m_land.geojson').read_text())
    rings=[]
    for feature in data['features']:
        geometry=feature['geometry']
        polygons=[geometry['coordinates']] if geometry['type']=='Polygon' else geometry['coordinates']
        rings.extend(p[0] for p in polygons)
    return rings

def map_rows(card,language,w,h,stamp,clean,dx=0.0,dy=0.0):
    width=min(w*.80,h*.46);height=width/2;left=(w-width)/2+(w*dx if dx else 0);top=h*.49-height/2+(h*dy if dy else 0)
    def xy(lon,lat):return left+(lon+180)/360*width,top+(90-lat)/180*height
    drawing=[]
    for ring in land():
        points=[xy(lon,lat) for lon,lat,*_ in ring]
        drawing.append('m '+' l '.join(f'{x:.1f} {y:.1f}' for x,y in points))
    tags=r'{\an7\pos(0,0)\p1\c&H00829377\fad(150,150)}'
    rows=f'Dialogue: 1,{stamp(card["start"])},{stamp(card["end"])},Default,,0,0,0,,{tags}'+ ' '.join(drawing)+'\n'
    for index,point in enumerate(card['locations']):
        x,y=xy(point['longitude'],point['latitude']);r=max(3,w*.005)
        at=card['start']+min(index*.2,(card['end']-card['start'])/2)
        pin=r'{\an7\pos(0,0)\p1\c&H0060DDFF\fad(150,100)}'+f'm {x-r:.1f} {y-r:.1f} l {x+r:.1f} {y-r:.1f} {x+r:.1f} {y+r:.1f} {x-r:.1f} {y+r:.1f}'
        label=clean(point['label'][language]);size=min(h*.018,width*.3/max(1,len(label)))
        tx=max(left+width*.15,min(left+width*.85,x))
        text=r'{\an5\pos('+f'{tx:.1f},{y-r-h*.012:.1f}'+r')\fs'+f'{size:.1f}'+r'\c&H00FFFFFF\bord1\fad(150,100)}'+label
        rows+=f'Dialogue: 2,{stamp(at)},{stamp(card["end"])},Default,,0,0,0,,{pin}\n'
        rows+=f'Dialogue: 3,{stamp(at)},{stamp(card["end"])},Default,,0,0,0,,{text}\n'
    return rows
