import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, computed, inject, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Api, errorMessage } from '../../core/api';
import { fileSize, kindIcon } from '../../core/format';
import { Icon } from '../../shared/icon';
import { LOCALE, TPipe, t } from '../../core/i18n';

type FileKind = 'image' | 'document' | 'audio';

interface Attachment {
  id: number;
  file: File;
  kind: FileKind;
  preview: string | null;
}

const ACCEPT: Record<FileKind, string> = {
  image: 'image/jpeg,image/png,image/webp,image/gif',
  document: '.pdf,.docx,.txt,.md,.html,.htm',
  audio: 'audio/*,.m4a,.mp3,.wav,.webm,.ogg',
};
const MAX_FILES = 6;
const MAX_MB = 20;

function kindOf(file: File): FileKind | null {
  if (file.type.startsWith('image/')) return 'image';
  if (file.type.startsWith('audio/') || /\.(mp3|wav|m4a|ogg|webm)$/i.test(file.name)) return 'audio';
  if (/\.(pdf|docx|txt|md|html?)$/i.test(file.name)) return 'document';
  return null;
}

@Component({
  selector: 'app-analyze-page',
  imports: [FormsModule, Icon, TPipe],
  templateUrl: './analyze-page.html',
  styleUrl: './analyze-page.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AnalyzePage {
  private readonly api = inject(Api);
  private readonly router = inject(Router);
  private readonly picker = viewChild.required<ElementRef<HTMLInputElement>>('picker');
  private readonly textarea = viewChild.required<ElementRef<HTMLTextAreaElement>>('textarea');

  protected readonly accept = ACCEPT;
  protected readonly text = signal('');
  protected readonly urlDraft = signal('');
  protected readonly urls = signal<string[]>([]);
  protected readonly attachments = signal<Attachment[]>([]);
  protected readonly pickerAccept = signal(ACCEPT.document);
  protected readonly submitting = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly dragging = signal(false);
  protected readonly menuOpen = signal(false);
  protected readonly recording = signal(false);
  protected readonly recordSeconds = signal(0);

  protected readonly count = computed(() => this.attachments().length + this.urls().length);
  protected readonly canSubmit = computed(
    () => !this.submitting() && !this.recording() && (this.text().trim().length > 0 || this.count() > 0),
  );
  protected readonly fileSize = fileSize;
  protected readonly kindIcon = kindIcon;

  private nextId = 1;
  private recorder: MediaRecorder | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    inject(DestroyRef).onDestroy(() => {
      this.stopRecording(false);
      this.attachments().forEach((a) => a.preview && URL.revokeObjectURL(a.preview));
    });
  }

  protected openPicker(kind: FileKind): void {
    this.pickerAccept.set(ACCEPT[kind]);
    // laisse Angular appliquer l'attribut accept avant d'ouvrir la fenêtre
    queueMicrotask(() => this.picker().nativeElement.click());
  }

  protected pick(kind: FileKind): void {
    this.menuOpen.set(false);
    this.openPicker(kind);
  }

  protected focusText(): void {
    this.textarea().nativeElement.focus();
  }

  protected onPicked(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.addFiles(Array.from(input.files ?? []));
    input.value = '';
  }

  protected onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(false);
    this.addFiles(Array.from(event.dataTransfer?.files ?? []));
  }

  protected onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(true);
  }

  private addFiles(files: File[]): void {
    this.error.set(null);
    for (const file of files) {
      const kind = kindOf(file);
      if (!kind) {
        this.error.set(`${file.name} : format non pris en charge (image, PDF, DOCX, TXT, HTML ou audio).`);
        continue;
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        this.error.set(`${file.name} dépasse ${MAX_MB} Mo.`);
        continue;
      }
      if (this.attachments().length >= MAX_FILES) {
        this.error.set(`${MAX_FILES} fichiers maximum par analyse.`);
        break;
      }
      const preview = kind === 'image' ? URL.createObjectURL(file) : null;
      this.attachments.update((list) => [...list, { id: this.nextId++, file, kind, preview }]);
    }
  }

  protected removeAttachment(a: Attachment): void {
    if (a.preview) URL.revokeObjectURL(a.preview);
    this.attachments.update((list) => list.filter((x) => x.id !== a.id));
  }

  protected addUrl(): void {
    const value = this.urlDraft().trim();
    if (!value) return;
    let parsed: URL;
    try {
      parsed = new URL(value);
    } catch {
      this.error.set(t('Lien invalide : collez une adresse complète commençant par https://'));
      return;
    }
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      this.error.set(t('Seuls les liens http et https sont acceptés.'));
      return;
    }
    if (!this.urls().includes(parsed.href)) this.urls.update((u) => [...u, parsed.href].slice(0, 10));
    this.urlDraft.set('');
    this.error.set(null);
  }

  protected removeUrl(url: string): void {
    this.urls.update((u) => u.filter((x) => x !== url));
  }

  protected hostOf(url: string): string {
    try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return url; }
  }

  // ---------- Enregistrement audio ----------
  protected async toggleRecording(): Promise<void> {
    if (this.recording()) {
      this.stopRecording(true);
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      this.error.set(t('Ce navigateur ne permet pas l’enregistrement : importez un fichier audio.'));
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: Blob[] = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        if ((recorder as MediaRecorder & { keep?: boolean }).keep && chunks.length) {
          const type = recorder.mimeType || 'audio/webm';
          const ext = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm';
          const stamp = new Date().toLocaleTimeString(LOCALE).replace(/:/g, 'h').slice(0, 5);
          this.addFiles([new File(chunks, `enregistrement-${stamp}.${ext}`, { type })]);
        }
      };
      recorder.start();
      this.recorder = recorder;
      this.recording.set(true);
      this.recordSeconds.set(0);
      this.timer = setInterval(() => {
        this.recordSeconds.update((s) => s + 1);
        if (this.recordSeconds() >= 300) this.stopRecording(true); // 5 minutes maximum
      }, 1000);
    } catch {
      this.error.set(t('Micro inaccessible : autorisez l’accès au micro ou importez un fichier audio.'));
    }
  }

  private stopRecording(keep: boolean): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    if (this.recorder && this.recorder.state !== 'inactive') {
      (this.recorder as MediaRecorder & { keep?: boolean }).keep = keep;
      this.recorder.stop();
    }
    this.recorder = null;
    this.recording.set(false);
  }

  protected formatSeconds(s: number): string {
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  }

  // ---------- Envoi ----------
  protected submit(): void {
    if (this.urlDraft().trim()) this.addUrl();
    if (!this.canSubmit()) return;
    this.submitting.set(true);
    this.error.set(null);
    this.api
      .createAnalysis({ text: this.text(), urls: this.urls(), files: this.attachments().map((a) => a.file) })
      .subscribe({
        next: (analysis) => this.router.navigate(['/resultat', analysis.id]),
        error: (err) => {
          this.error.set(errorMessage(err));
          this.submitting.set(false);
        },
      });
  }

  protected onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      this.submit();
    }
  }
}
