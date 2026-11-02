import { ClaimVerdict, GlobalVerdict, Stance, Workflow } from './models';

export type Tone = 'good' | 'mid' | 'bad' | 'neutral';

export function scoreTone(score: number | null | undefined): Tone {
  if (score === null || score === undefined) return 'neutral';
  if (score >= 6.5) return 'good';
  if (score >= 4.5) return 'mid';
  return 'bad';
}

export function toneColor(tone: Tone): string {
  return { good: 'var(--good)', mid: 'var(--mid)', bad: 'var(--bad)', neutral: 'var(--ink3)' }[tone];
}

export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '–';
  return score.toFixed(1).replace('.', ',');
}

export function pct(value: number): string {
  return `${Math.round(value * 100)} %`;
}

export const GLOBAL_VERDICTS: { key: GlobalVerdict; label: string; tone: Tone }[] = [
  { key: 'fiable', label: 'Fiables', tone: 'good' },
  { key: 'plutot_fiable', label: 'Plutôt fiables', tone: 'good' },
  { key: 'a_verifier', label: 'À vérifier', tone: 'mid' },
  { key: 'douteux', label: 'Douteuses', tone: 'bad' },
];

export function claimTone(v: ClaimVerdict): Tone {
  if (v === 'vrai' || v === 'plutot_vrai') return 'good';
  if (v === 'faux' || v === 'plutot_faux') return 'bad';
  if (v === 'mitige') return 'mid';
  return 'neutral';
}

export const STANCE_LABEL: Record<Stance, string> = {
  supports: 'Confirme',
  refutes: 'Contredit',
  context: 'Contexte',
};

export function stanceTone(s: Stance): Tone {
  return s === 'supports' ? 'good' : s === 'refutes' ? 'bad' : 'neutral';
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'n.d.';
  const abs = Math.abs(value);
  const fmt = (n: number, d = 2) => n.toLocaleString('fr-FR', { maximumFractionDigits: d });
  if (abs >= 1e9) return `${fmt(value / 1e9)} milliards`;
  if (abs >= 1e6) return `${fmt(value / 1e6)} millions`;
  return fmt(value, abs < 10 ? 2 : 1);
}

export function kindIcon(kind: string): { icon: string; tone: string } {
  switch (kind) {
    case 'image': return { icon: 'image', tone: 'tone-blue' };
    case 'document': return { icon: 'document', tone: 'tone-orange' };
    case 'audio': return { icon: 'audio', tone: 'tone-green' };
    case 'url': return { icon: 'link', tone: 'tone-grey' };
    case 'text': return { icon: 'text', tone: 'tone-purple' };
    default: return { icon: 'layers', tone: 'tone-grey' };
  }
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`;
  return `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} Mo`;
}

export function dayGroup(iso: string, now = new Date()): string {
  const d = new Date(iso);
  const start = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const days = Math.round((start(now) - start(d)) / 86_400_000);
  if (days <= 0) return 'Aujourd’hui';
  if (days === 1) return 'Hier';
  if (days < 7) return 'Cette semaine';
  if (days < 31) return 'Ce mois-ci';
  return 'Plus ancien';
}

export function relativeTime(iso: string, now = new Date()): string {
  const minutes = Math.round((now.getTime() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return 'à l’instant';
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `il y a ${hours} h`;
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
}

export const WORKFLOWS: { key: Workflow; label: string; tone: string }[] = [
  { key: 'a_traiter', label: 'À traiter', tone: 'tone-grey' },
  { key: 'en_revue', label: 'En revue', tone: 'tone-amber' },
  { key: 'valide', label: 'Validée', tone: 'tone-green' },
  { key: 'publie', label: 'Publiée', tone: 'tone-blue' },
  { key: 'archive', label: 'Archivée', tone: 'tone-purple' },
];

export function workflowLabel(w: Workflow): string {
  return WORKFLOWS.find((x) => x.key === w)?.label ?? w;
}

export function verdictLabel(v: GlobalVerdict | null | undefined): string {
  const labels: Record<GlobalVerdict, string> = {
    fiable: 'Fiable', plutot_fiable: 'Plutôt fiable', a_verifier: 'À vérifier', douteux: 'Douteux',
  };
  return v ? labels[v] : 'Sans verdict';
}

export function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]!.toUpperCase()).join('') || '?';
}

/** Teinte stable d'un avatar, dérivée de l'identifiant. */
export function avatarTone(id: string): string {
  const tones = ['tone-blue', 'tone-orange', 'tone-purple', 'tone-green', 'tone-amber', 'tone-red'];
  let h = 0;
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return tones[h % tones.length]!;
}
