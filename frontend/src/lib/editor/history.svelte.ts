/**
 * Undo and redo.
 *
 * Every editor action is saved on the server straight away, so undo cannot just
 * swap local state. Instead the editor remembers the whole timeline before each
 * action (a snapshot) and, to undo, asks the server to restore it
 * (PUT /projects/{id}/scenes/timeline). Redo is the same with the snapshot taken
 * just before the undo.
 */
import type { Project, Scene, TimelineSnapshot } from '$lib/types/api';

const LIMIT = 60;

export const takeSnapshot = (
  scenes: Scene[],
  project: Pick<Project, 'music' | 'music_asset_id'>
): TimelineSnapshot => ({
  scenes: [...scenes]
    .sort((a, b) => a.scene_number - b.scene_number)
    .map((scene) => ({
      id: scene.id,
      narration: scene.narration,
      visual_prompt: scene.visual_prompt,
      on_screen_text: scene.on_screen_text,
      duration: scene.duration,
      transition: scene.transition,
      background_color: scene.background_color,
      language: scene.language,
      settings: structuredClone($state.snapshot(scene.settings)),
      image_asset_id: scene.image_asset_id,
      video_asset_id: scene.video_asset_id,
      audio_asset_id: scene.audio_asset_id,
      captions: scene.captions.map((c) => ({
        text: c.text,
        start_time: c.start_time,
        end_time: c.end_time,
        language: c.language
      }))
    })),
  music_asset_id: project.music_asset_id,
  music: { ...project.music }
});

export class History {
  #undo: TimelineSnapshot[] = [];
  #redo: TimelineSnapshot[] = [];
  canUndo = $state(false);
  canRedo = $state(false);

  #sync() {
    this.canUndo = this.#undo.length > 0;
    this.canRedo = this.#redo.length > 0;
  }

  /** Call BEFORE an action changes anything. A new action ends the redo chain. */
  record(snapshot: TimelineSnapshot) {
    this.#undo.push(snapshot);
    if (this.#undo.length > LIMIT) this.#undo.shift();
    this.#redo = [];
    this.#sync();
  }

  /** Pops the state to go back to, remembering `current` for redo. */
  undo(current: TimelineSnapshot): TimelineSnapshot | null {
    const previous = this.#undo.pop();
    if (!previous) return null;
    this.#redo.push(current);
    this.#sync();
    return previous;
  }

  redo(current: TimelineSnapshot): TimelineSnapshot | null {
    const next = this.#redo.pop();
    if (!next) return null;
    this.#undo.push(current);
    this.#sync();
    return next;
  }

  /** Puts a snapshot back after a failed undo/redo so the stacks stay truthful. */
  rollback(kind: 'undo' | 'redo', taken: TimelineSnapshot) {
    if (kind === 'undo') {
      this.#redo.pop();
      this.#undo.push(taken);
    } else {
      this.#undo.pop();
      this.#redo.push(taken);
    }
    this.#sync();
  }

  /** Forgets the snapshot recorded for an action that then failed to change anything. */
  discardLast() {
    this.#undo.pop();
    this.#sync();
  }

  clear() {
    this.#undo = [];
    this.#redo = [];
    this.#sync();
  }
}
