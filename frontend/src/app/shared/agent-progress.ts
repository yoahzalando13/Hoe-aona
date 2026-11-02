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

type AgentState = 'todo' | 'working' | 'done' | 'error';

@Component({
  selector: 'app-agent-progress',
  imports: [Icon, TPipe],
  templateUrl: './agent-progress.html',
  styleUrl: './agent-progress.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AgentProgress {
  readonly analysis = input.required<AnalysisOut>();
  /** `live` : analyse en cours (équipe + journal) ; `log` : journal seul, une fois l'analyse terminée. */
  readonly mode = input<'live' | 'log'>('live');

  private readonly logBox = viewChild<ElementRef<HTMLElement>>('logBox');
  private readonly now = signal(Date.now());
  protected readonly follow = signal(true);
  protected readonly agents = AGENTS;

  protected readonly events = computed(() => this.analysis().events ?? []);
  protected readonly running = computed(() => this.analysis().status === 'pending' || this.analysis().status === 'running');

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

  protected readonly toolStats = computed(() => {
    const calls = this.events().filter((e) => e.tool);
    return {
      total: calls.length,
      ok: calls.filter((e) => e.status === 'done').length,
      failed: calls.filter((e) => e.status === 'error').length,
      active: calls.filter((e) => e.status === 'running').length,
    };
  });

  protected readonly claimsFound = computed(() =>
    this.events().filter((e) => e.agent === 'extracteur' && e.status === 'info').length);

  constructor() {
    const timer = setInterval(() => this.now.set(Date.now()), 1000);
    inject(DestroyRef).onDestroy(() => clearInterval(timer));
    // Défilement automatique du journal tant que l'utilisateur n'est pas remonté le lire.
    effect(() => {
      this.events();
      const box = this.logBox()?.nativeElement;
      if (box && this.follow() && this.mode() === 'live') queueMicrotask(() => box.scrollTop = box.scrollHeight);
    });
  }

  protected state(agent: Agent): AgentState {
    const mine = this.events().filter((e) => e.agent === agent.key);
    const p = this.analysis().progress;
    if (this.analysis().status === 'error' && mine.some((e) => e.status === 'error')) return 'error';
    if (mine.some((e) => e.status === 'running')) return 'working';
    if (p >= agent.to || this.analysis().status === 'done') return 'done';
    if (p >= agent.from && this.running()) return 'working';
    return mine.length ? 'done' : 'todo';
  }

  /** Dernière action d'un agent, pour la ligne d'activité sous son nom. */
  protected activity(agent: Agent): string {
    const mine = this.events().filter((e) => e.agent === agent.key);
    const live = [...mine].reverse().find((e) => e.status === 'running');
    const last = live ?? mine[mine.length - 1];
    if (!last) return agent.role;
    return last.detail && !live ? `${last.message} · ${last.detail}` : last.message;
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
