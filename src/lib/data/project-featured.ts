import { mediaApi, ownerToken } from './media-api';
import { SignInRequired } from './titles';

export async function setFeaturedTake(runId: string, artifactId: string): Promise<void> {
  const token = ownerToken();
  if (!token) throw new SignInRequired('Sign in to set the hero take.');
  const response = await fetch(`${mediaApi}/runs/${encodeURIComponent(runId)}/featured`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ artifact_id: artifactId }),
  });
  if (response.status === 401) {
    throw new SignInRequired('Your session expired. Sign in again to set the hero take.');
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { error?: string } | null;
    throw new Error(body?.error ?? 'Could not set the hero take.');
  }
}