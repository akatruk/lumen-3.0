export function musicAccents(accents:number[],trackDuration:number,offset:number,outputDuration:number):number[]{
 const length=trackDuration-offset;
 if(length<.1||outputDuration<=0)return [];
 const source=accents.filter(t=>t>=offset&&t<trackDuration).map(t=>t-offset);
 const mapped:number[]=[];
 for(let base=0;base<outputDuration;base+=length){
  for(const t of source){if(base+t<outputDuration)mapped.push(base+t);if(mapped.length>=5000)return mapped;}
 }
 return mapped;
}
export function alignedOffset(accents:number[],trackDuration:number,cut:number,current:number):number|null{
 const candidates=accents.map(t=>t-cut).filter(t=>t>=0&&t<trackDuration-.1);
 return candidates.length?candidates.reduce((best,t)=>Math.abs(t-current)<Math.abs(best-current)?t:best):null;
}
