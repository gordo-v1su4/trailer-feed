import { mediaApi, ownerToken } from './media-api';
import { SignInRequired } from './titles';

/** Removes one externally owned version and retains its suppression marker. */
export async function removeExternalVersion(input: { runId:string; artifactId:string; generation:number }): Promise<void> {
  const token = ownerToken();
  if (!token) throw new SignInRequired('Sign in to remove this version from Trailer Feed.');
  const response = await fetch(`${mediaApi}/versions/${encodeURIComponent(input.artifactId)}/remove`, {
    method:'POST',
    headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`},
    body:JSON.stringify({run_id:input.runId,confirm_artifact_id:input.artifactId,expected_generation:input.generation}),
  });
  if (response.status === 401) {
    sessionStorage.removeItem('trailer-feed-owner');
    throw new SignInRequired('Your session expired. Sign in again to remove this version.');
  }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.error || 'Version removal failed. Retry the same version.');
}
