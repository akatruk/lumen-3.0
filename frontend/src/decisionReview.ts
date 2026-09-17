/** Editing a shot invalidates its previous review; metadata changes do not. */
export function reviseDecision<T extends {approved?:boolean;locked?:boolean}>(current:T, patch:Partial<T>):T {
  const keys=Object.keys(patch) as (keyof T)[];
  const changed=keys.filter(key=>JSON.stringify(current[key])!==JSON.stringify(patch[key]));
  if(current.locked && changed.some(key=>key!=='locked'))return current;
  const renderChanged=changed.some(key=>!['id','approved','locked','shot_type'].includes(String(key)));
  return {...current,...patch,...(renderChanged?{approved:false,locked:false}:{})};
}
