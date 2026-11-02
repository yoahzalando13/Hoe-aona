import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, computed, effect, inject, input, signal, viewChild } from '@angular/core';
import { AgentEvent, AgentKey, AnalysisOut } from '../core/models';
import { Icon } from './icon';
import { TPipe, t } from '../core/i18n';

interface Agent { key: AgentKey; name: string; role: string; icon: string; from: number; to: number; }

/** Les agents de l'analyse, dans l'ordre du pipeline, avec leur plage sur la barre de progression. */
const AGENTS: Agent[] = [
  { key: 'lecteur', name: t('Lecteur'), role: t('Lit textes, pages, images et audios'), icon: 'document', from: 0, to: 20 },
  { key: 'detecteur', name: t('Détecteur IA'), role: t('Cherche les signatures de génération'), icon: 'robot', from: 20, to: 30 },
  { key: 'extracteur', name: t('Extracteur'), role: t('Isole les affirmations vérifiables'), icon: 'text', from: 30, to: 45 },
  { key: 'chercheur', name: t('Chercheur'), role: t('Interroge les sources via MCP'), icon: 'search', from: 45, to: 75 },
  { key: 'evaluateur', name: t('Évaluateur'), role: t('Confronte preuves et raisonnements'), icon: 'verify', from: 75, to: 88 },
  { key: 'calculateur', name: t('Calculateur'), role: t('Pondère les trois critères'), icon: 'gauge', from: 88, to: 95 },
  { key: 'redacteur', name: t('Rédacteur'), role: t('Écrit l’article suggéré'), icon: 'edit', from: 95, to: 100 },
];

@Component({
  selector: 'app-agent-progress',
  imports: [Icon, TPipe],
  templateUrl: './agent-progress.html',
  styleUrl: './agent-progress.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AgentProgress {
  readonly analysis = input.required<AnalysisOut>();
  /** `live` : étapes révélées une à une pendant l'analyse ; `log` : journal complet, une fois l'analyse terminée. */
  readonly mode = input<'live' | 'log'>('live');

  private readonly logBox = viewChild<ElementRef<HTMLElement>>('logBox');
  private readonly stepsBox = viewChild<ElementRef<HTMLElement>>('stepsBox');
  /** Nombre d'étapes déjà affichées : en direct, elles apparaissent une par une. */
  private readonly revealed = signal(0);
  private revealTimer: ReturnType<typeof setInterval> | null = null;
  private readonly now = signal(Date.now());
  protected readonly follow = signal(true);

  protected readonly events = computed(() => this.analysis().events ?? []);
  protected readonly running = computed(() => this.analysis().status === 'pending' || this.analysis().status === 'running');

  /** Étapes visibles en direct (leur statut, lui, suit toujours la dernière mise à jour du serveur). */
  protected readonly shown = computed(() => this.events().slice(0, this.revealed()));
  /** Étape portant les trois points animés : la dernière affichée encore en cours, sinon la dernière affichée. */
  protected readonly activeIndex = computed(() => {
    const list = this.shown();
    if (!this.running()) return -1;
    for (let i = list.length - 1; i >= 0; i--) if (list[i].status === 'running') return i;
    return list.length - 1;
  });

  protected readonly elapsed = computed(() => {
    const a = this.analysis();
    const start = new Date(a.created_at).getTime();
    const end = this.running() ? this.now() : new Date(a.updated_at).getTime();
    return Math.max(0, (end - start) / 1000);
  });

  /** Estimation simple : temps écoulé rapporté à l'avancement, affichée seulement quand elle a du sens. */
  protected readonly remaining = computed(() => {
    const p = this.analysis().progress;
    const t = this.elapsed();
    if (!this.running() || p < 10 || t < 5) return null;
    return Math.max(5, Math.round((t * (100 - p)) / p));
  });

  constructor() {
    const timer = setInterval(() => this.now.set(Date.now()), 1000);
    inject(DestroyRef).onDestroy(() => {
      clearInterval(timer);
      if (this.revealTimer) clearInterval(this.revealTimer);
    });
    // Révélation progressive : une étape toutes les 350 ms tant qu'il en reste à afficher.
    effect(() => {
      const total = this.events().length;
      if (this.mode() === 'log') { this.revealed.set(total); return; }
      if (this.revealed() > total) this.revealed.set(total);
      if (this.revealed() < total && !this.revealTimer) {
        this.revealTimer = setInterval(() => {
          if (this.revealed() >= this.events().length) {
            clearInterval(this.revealTimer!);
            this.revealTimer = null;
            return;
          }
          this.revealed.update((n) => n + 1);
          const box = this.stepsBox()?.nativeElement;
          if (box && this.follow()) queueMicrotask(() => box.scrollTop = box.scrollHeight);
        }, 350);
      }
    });
    // Défilement automatique du journal tant que l'utilisateur n'est pas remonté le lire.
    effect(() => {
      this.events();
      const box = this.logBox()?.nativeElement;
      if (box && this.follow() && this.mode() === 'live') queueMicrotask(() => box.scrollTop = box.scrollHeight);
    });
  }

  protected agentName(key: AgentKey): string {
    return AGENTS.find((a) => a.key === key)?.name ?? key;
  }

  protected agentIcon(key: AgentKey): string {
    return AGENTS.find((a) => a.key === key)?.icon ?? 'sparkle';
  }

  protected onScroll(event: Event): void {
    const el = event.target as HTMLElement;
    this.follow.set(el.scrollHeight - el.scrollTop - el.clientHeight < 40);
  }

  protected seconds(s: number): string {
    if (s < 60) return `${Math.round(s)} s`;
    return `${Math.floor(s / 60)} min ${String(Math.round(s % 60)).padStart(2, '0')} s`;
  }

  protected stamp(e: AgentEvent): string {
    return '+' + e.at.toFixed(1).replace('.', ',') + ' s';
  }

  protected trackEvent(index: number, e: AgentEvent): string {
    return `${index}-${e.agent}-${e.at}`;
  }
}
