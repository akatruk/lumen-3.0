const seed=require('./workspace.cjs');
module.exports=function fixture(){
 const d=structuredClone(seed),text={en:'A useful improvement',zh:'改进'},musicId='1'.repeat(32),videoId='2'.repeat(32);
 d.assets=[{id:musicId,title:'QA music',attribution:'QA owned',metadata:{duration:30,kind:'music'}},{id:videoId,title:'QA B-roll',attribution:'QA owned',metadata:{duration:12,kind:'video'}}];
 d.soundtracks=[{key:'qa-track',title:'QA soundtrack',artist:'QA artist',origin:'curated',mood:'calm',duration:30,attribution:'QA owned',favorite:false,available:true}];
 d.music={asset_id:musicId,source_start:0,gain_db:-24,fade_in:1,fade_out:2,duck:true};
 d.creative=[];d.proposals=[];d.musicPlans=[];d.alternatives=[];
 const rec={id:'cut',start:2,end:4,title:text,evidence:text,improvement:text,category:'pacing',confidence:.7,auto_apply:false,action:'remove',generation_prompt:''};
 d.studio.plan.recommendations=[rec];d.studio.decisions=[{id:'cut',start:2,end:4,approved:true,locked:false}];
 d.studio.context.platforms=['tiktok'];
 const variant={platform:'tiktok',title:'QA title',description:'QA description',hashtags:['#qa'],cta:'See more',rationale:text,metadata:d.project.metadata,segments:[{start:0,end:6},{start:6,end:12}],review_status:'needs_review',locked:false,caption_editable:true,aspect:'9:16'};
 d.pack={status:'complete',package_id:'pack1',master_id:d.project.result.render_id,stale:false,result:{variants:[variant],scene_boundaries:[0,6,12]}};
 d.history=[{package_id:'pack0',created:1700000000}];
 d.search={items:[{id:'ref1',aweme_id:'1234567890123456789',title:'QA reference',author:'QA',duration:12,likes:10,cover:null,share_url:'https://www.douyin.com/video/1234567890123456789'}],continuation:'next',keyword:'travel'};
 return d;
};
