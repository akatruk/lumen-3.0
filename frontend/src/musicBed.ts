export type BedAsset = {
  id: string;
  metadata: {catalogue_id?: string; reused_from?: string};
};

export function bedKeyForAsset(asset: BedAsset | undefined | null): string {
  if (!asset) return '';
  if (asset.metadata.catalogue_id) return 'curated:' + asset.metadata.catalogue_id;
  const reused = asset.metadata.reused_from || '';
  if (reused.startsWith('curated:')) return reused;
  return 'asset:' + asset.id;
}

export function projectAssetForTrack(trackKey: string, assets: BedAsset[]): string | null {
  if (trackKey.startsWith('curated:')) {
    const catalogue = trackKey.slice('curated:'.length);
    const hit = assets.find(asset => asset.metadata.catalogue_id === catalogue || asset.metadata.reused_from === trackKey);
    return hit ? hit.id : null;
  }
  if (trackKey.startsWith('asset:')) {
    const id = trackKey.slice(6);
    return assets.some(asset => asset.id === id) ? id : null;
  }
  return null;
}

export function toggleCandidate(chosen: string[], id: string, on: boolean, max = 3): string[] {
  if (!id) return chosen;
  if (!on) return chosen.filter(item => item !== id);
  if (chosen.includes(id) || chosen.length >= max) return chosen;
  return [...chosen, id];
}

export function formatClock(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
  const whole = Math.floor(seconds);
  return Math.floor(whole / 60) + ':' + String(whole % 60).padStart(2, '0');
}

/** A bed row stays clickable during renders and unsaved edits. Only a missing file blocks it. */
export function bedControlDisabled(available: boolean): boolean {
  return !available;
}

/** AI candidate checks are independent of render/dirty/lock. The cap still applies. */
export function candidateControlDisabled(input: {busy: boolean; checked: boolean; chosen: number; available: boolean}): boolean {
  return input.busy || !input.available || (!input.checked && input.chosen >= 3);
}
