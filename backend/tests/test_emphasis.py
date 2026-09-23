import subprocess
import pytest
from backend.schemas import Caption
from backend.media import ass_available,emphasize_caption,write_subtitles,ffmpeg

def test_highlights_preserve_words_and_ignore_ass_injection(tmp_path):
 text=emphasize_caption('Thailand and land',['land'],'en','&H00FFFFFF')
 assert text.startswith('Thailand and {') and text.count('{\\c&H0000FFFF}')==1
 assert emphasize_caption('One\\Ncountry',['One country'],'en','&H00FFFFFF').count('{\\c&H0000FFFF}')==1
 c=Caption(start=0,end=1,original='',en='Travel 2026 {\\pos(1,1)}',zh='旅行2026',emphasis_en=['2026'],emphasis_zh=['2026'])
 out=tmp_path/'en.ass';write_subtitles(out,[c],[(0,1)],'en',320,568)
 assert '{\\pos' not in out.read_text() and '{\\c&H0000FFFF}2026' in out.read_text()
 out=tmp_path/'zh.ass';write_subtitles(out,[c],[(0,1)],'zh',320,568,{'color':'yellow'})
 assert '{\\c&H00FFFF00}2026' in out.read_text()
 with pytest.raises(ValueError):Caption.model_validate(c.model_dump()|{'emphasis_en':['x']*9})

@pytest.mark.skipif(not ass_available(),reason='FFmpeg ass filter required')
@pytest.mark.parametrize('language',['en','zh'])
def test_emphasis_has_colored_pixels_in_real_render(tmp_path,language):
 c=Caption(start=0,end=2,original='',en='Travel 2026',zh='旅行2026',emphasis_en=['2026'],emphasis_zh=['2026'])
 ass=tmp_path/'captions.ass';write_subtitles(ass,[c],[(0,2)],language,320,568)
 out=tmp_path/'result.mp4'
 ffmpeg('-f','lavfi','-i','color=black:s=320x568:d=2:r=12','-vf',f"ass='{ass}'",'-c:v','libx264',out)
 raw=subprocess.check_output(['ffmpeg','-v','error','-ss','1','-i',str(out),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
 pixels=list(zip(raw[0::3],raw[1::3],raw[2::3]))
 assert sum(r>150 and g>150 and b<100 for r,g,b in pixels)>30
 assert sum(r>180 and g>180 and b>180 for r,g,b in pixels)>30
 ffmpeg('-ss',1,'-i',out,'-frames:v','1',tmp_path/'preview.png')
