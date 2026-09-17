import pytest
from backend.visuals import VisualCard,MapPoint,write_card
from backend.tests.test_studio import T,plan

def test_map_coordinates_and_card_types_are_validated():
    with pytest.raises(ValueError):MapPoint(label=T,latitude=91,longitude=0)
    with pytest.raises(ValueError):VisualCard(kind='map',start=0,end=2,title=T,primary=T,source=T)
    with pytest.raises(ValueError):VisualCard(kind='number',start=0,end=2,title=T,primary=T,source=T,locations=[MapPoint(label=T,latitude=0,longitude=0)])

def test_map_reaches_real_renderer(tmp_path):
    from backend import media
    from backend.manual import Edit,Clip
    source=tmp_path/'source.mp4'
    media.ffmpeg('-f','lavfi','-i','color=black:s=540x960:d=2:r=30','-c:v','libx264',source)
    card=VisualCard(kind='map',start=0,end=2,title={'en':'Locations','zh':'地点'},primary=T,source={'en':'Natural Earth / supplied coordinates','zh':'Natural Earth／提供的坐标'},locations=[MapPoint(label={'en':'Point A','zh':'地点 A'},latitude=14,longitude=101),MapPoint(label={'en':'Point B','zh':'地点 B'},latitude=40,longitude=116)])
    edit=Edit(clips=[Clip(start=0,end=2,card=card)])
    result=media.render(source,tmp_path,media.probe(source),plan(),[],'en','original',manual=edit.model_dump())
    assert result['director_timeline']['tracks']['inserts'][0]['kind']=='map'
    media.ffmpeg('-ss',1,'-i',tmp_path/'result.mp4','-frames:v',1,tmp_path/'map-preview.png')
    assert (tmp_path/'map-preview.png').stat().st_size>1000
