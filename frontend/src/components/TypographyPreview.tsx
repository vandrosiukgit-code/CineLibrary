/* eslint-disable react-refresh/only-export-components */
import type { CSSProperties } from 'react'
import './TypographyPreview.css'

export interface TypographyVariant {
  id: number
  name: string
  cineFont: string
  libraryFont: string
  cineWeight: number
  libraryWeight: number
  cineStyle: 'normal' | 'italic'
  libraryStyle: 'normal' | 'italic'
  cineSize: number
  librarySize: number
  cineSpacing: string
  librarySpacing: string
  lineHeight: number
  baselineAdjustment: string
}

export const TYPOGRAPHY_STORAGE_KEY = 'cinelibrary_typography_variant'

export const TYPOGRAPHY_VARIANTS: TypographyVariant[] = [
  { id: 1, name: 'Manrope + Cormorant Garamond — элегантная классика', cineFont: 'Manrope', libraryFont: 'Cormorant Garamond', cineWeight: 600, libraryWeight: 600, cineStyle: 'normal', libraryStyle: 'italic', cineSize: 47, librarySize: 54, cineSpacing: '-0.04em', librarySpacing: '-0.025em', lineHeight: 1.08, baselineAdjustment: '0.04em' },
  { id: 2, name: 'Inter + Playfair Display — киножурнал', cineFont: 'Inter', libraryFont: 'Playfair Display', cineWeight: 600, libraryWeight: 500, cineStyle: 'normal', libraryStyle: 'italic', cineSize: 46, librarySize: 49, cineSpacing: '-0.045em', librarySpacing: '-0.025em', lineHeight: 1.1, baselineAdjustment: '0.01em' },
  { id: 3, name: 'DM Sans + DM Serif Display — редакционный', cineFont: 'DM Sans', libraryFont: 'DM Serif Display', cineWeight: 600, libraryWeight: 400, cineStyle: 'normal', libraryStyle: 'italic', cineSize: 47, librarySize: 50, cineSpacing: '-0.045em', librarySpacing: '-0.02em', lineHeight: 1.08, baselineAdjustment: '0.02em' },
  { id: 4, name: 'Plus Jakarta Sans + Libre Baskerville — интеллигентный', cineFont: 'Plus Jakarta Sans', libraryFont: 'Libre Baskerville', cineWeight: 600, libraryWeight: 400, cineStyle: 'normal', libraryStyle: 'italic', cineSize: 44, librarySize: 43, cineSpacing: '-0.05em', librarySpacing: '-0.03em', lineHeight: 1.12, baselineAdjustment: '-0.01em' },
  { id: 5, name: 'Outfit + Fraunces — авторское кино', cineFont: 'Outfit', libraryFont: 'Fraunces', cineWeight: 500, libraryWeight: 500, cineStyle: 'normal', libraryStyle: 'normal', cineSize: 48, librarySize: 50, cineSpacing: '-0.04em', librarySpacing: '-0.035em', lineHeight: 1.08, baselineAdjustment: '0.01em' },
  { id: 6, name: 'Sora + Cormorant Garamond — архивный', cineFont: 'Sora', libraryFont: 'Cormorant Garamond', cineWeight: 600, libraryWeight: 500, cineStyle: 'normal', libraryStyle: 'normal', cineSize: 44, librarySize: 55, cineSpacing: '-0.05em', librarySpacing: '-0.035em', lineHeight: 1.08, baselineAdjustment: '0.05em' },
  { id: 7, name: 'Montserrat + Bodoni Moda — премиальный', cineFont: 'Montserrat', libraryFont: 'Bodoni Moda', cineWeight: 500, libraryWeight: 500, cineStyle: 'normal', libraryStyle: 'italic', cineSize: 44, librarySize: 48, cineSpacing: '-0.045em', librarySpacing: '-0.03em', lineHeight: 1.12, baselineAdjustment: '0' },
  { id: 8, name: 'Manrope + Prata — благородный', cineFont: 'Manrope', libraryFont: 'Prata', cineWeight: 600, libraryWeight: 400, cineStyle: 'normal', libraryStyle: 'normal', cineSize: 46, librarySize: 43, cineSpacing: '-0.045em', librarySpacing: '-0.035em', lineHeight: 1.12, baselineAdjustment: '-0.025em' },
  { id: 9, name: 'Inter + Lora — мягкий классический', cineFont: 'Inter', libraryFont: 'Lora', cineWeight: 500, libraryWeight: 500, cineStyle: 'normal', libraryStyle: 'italic', cineSize: 47, librarySize: 47, cineSpacing: '-0.04em', librarySpacing: '-0.025em', lineHeight: 1.1, baselineAdjustment: '0' },
  { id: 10, name: 'Urbanist + Playfair Display — современная классика', cineFont: 'Urbanist', libraryFont: 'Playfair Display', cineWeight: 600, libraryWeight: 500, cineStyle: 'normal', libraryStyle: 'normal', cineSize: 49, librarySize: 47, cineSpacing: '-0.05em', librarySpacing: '-0.035em', lineHeight: 1.08, baselineAdjustment: '-0.015em' },
  { id: 11, name: 'Manrope + Manrope — чистый минимализм', cineFont: 'Manrope', libraryFont: 'Manrope', cineWeight: 500, libraryWeight: 700, cineStyle: 'normal', libraryStyle: 'normal', cineSize: 48, librarySize: 48, cineSpacing: '-0.045em', librarySpacing: '-0.045em', lineHeight: 1.1, baselineAdjustment: '0' },
  { id: 12, name: 'Outfit + Outfit — лаконичный', cineFont: 'Outfit', libraryFont: 'Outfit', cineWeight: 500, libraryWeight: 300, cineStyle: 'normal', libraryStyle: 'normal', cineSize: 50, librarySize: 50, cineSpacing: '-0.04em', librarySpacing: '-0.035em', lineHeight: 1.08, baselineAdjustment: '0' },
  { id: 13, name: 'Space Grotesk + Space Grotesk — современное кино', cineFont: 'Space Grotesk', libraryFont: 'Space Grotesk', cineWeight: 600, libraryWeight: 400, cineStyle: 'normal', libraryStyle: 'normal', cineSize: 47, librarySize: 47, cineSpacing: '-0.055em', librarySpacing: '-0.04em', lineHeight: 1.1, baselineAdjustment: '0' },
  { id: 14, name: 'Sora + Sora — цифровая эстетика', cineFont: 'Sora', libraryFont: 'Sora', cineWeight: 500, libraryWeight: 300, cineStyle: 'normal', libraryStyle: 'normal', cineSize: 44, librarySize: 44, cineSpacing: '-0.05em', librarySpacing: '-0.035em', lineHeight: 1.12, baselineAdjustment: '0' },
  { id: 15, name: 'Plus Jakarta Sans + Plus Jakarta Sans — строгий премиум', cineFont: 'Plus Jakarta Sans', libraryFont: 'Plus Jakarta Sans', cineWeight: 700, libraryWeight: 400, cineStyle: 'normal', libraryStyle: 'normal', cineSize: 44, librarySize: 44, cineSpacing: '-0.055em', librarySpacing: '-0.04em', lineHeight: 1.12, baselineAdjustment: '0' },
  { id: 16, name: 'DM Sans + Fraunces — кинофестиваль', cineFont: 'DM Sans', libraryFont: 'Fraunces', cineWeight: 600, libraryWeight: 400, cineStyle: 'normal', libraryStyle: 'italic', cineSize: 47, librarySize: 49, cineSpacing: '-0.045em', librarySpacing: '-0.025em', lineHeight: 1.08, baselineAdjustment: '0.01em' },
  { id: 17, name: 'Manrope + Bodoni Moda — европейский', cineFont: 'Manrope', libraryFont: 'Bodoni Moda', cineWeight: 600, libraryWeight: 500, cineStyle: 'normal', libraryStyle: 'normal', cineSize: 46, librarySize: 48, cineSpacing: '-0.045em', librarySpacing: '-0.035em', lineHeight: 1.1, baselineAdjustment: '0' },
  { id: 18, name: 'Inter + Cormorant Garamond — классический архив', cineFont: 'Inter', libraryFont: 'Cormorant Garamond', cineWeight: 600, libraryWeight: 600, cineStyle: 'normal', libraryStyle: 'normal', cineSize: 45, librarySize: 54, cineSpacing: '-0.045em', librarySpacing: '-0.035em', lineHeight: 1.08, baselineAdjustment: '0.045em' },
  { id: 19, name: 'Outfit + Playfair Display — художественный', cineFont: 'Outfit', libraryFont: 'Playfair Display', cineWeight: 600, libraryWeight: 400, cineStyle: 'normal', libraryStyle: 'italic', cineSize: 48, librarySize: 48, cineSpacing: '-0.04em', librarySpacing: '-0.025em', lineHeight: 1.08, baselineAdjustment: '0' },
  { id: 20, name: 'Urbanist + Cormorant Garamond — утончённый', cineFont: 'Urbanist', libraryFont: 'Cormorant Garamond', cineWeight: 500, libraryWeight: 600, cineStyle: 'normal', libraryStyle: 'italic', cineSize: 49, librarySize: 55, cineSpacing: '-0.045em', librarySpacing: '-0.025em', lineHeight: 1.08, baselineAdjustment: '0.045em' },
]

type WordmarkStyle = CSSProperties & Record<`--${string}`, string | number>

export function getTypographyVariant(id: number): TypographyVariant {
  return TYPOGRAPHY_VARIANTS.find((variant) => variant.id === id) ?? TYPOGRAPHY_VARIANTS[0]
}

export function CineLibraryWordmark({ variant }: { variant: TypographyVariant }) {
  const style: WordmarkStyle = {
    '--cine-font': `"${variant.cineFont}", "Segoe UI", sans-serif`,
    '--library-font': `"${variant.libraryFont}", Georgia, serif`,
    '--cine-weight': variant.cineWeight,
    '--library-weight': variant.libraryWeight,
    '--cine-style': variant.cineStyle,
    '--library-style': variant.libraryStyle,
    '--cine-size': `${variant.cineSize}px`,
    '--library-size': `${variant.librarySize}px`,
    '--cine-spacing': variant.cineSpacing,
    '--library-spacing': variant.librarySpacing,
    '--wordmark-line-height': variant.lineHeight,
    '--library-baseline': variant.baselineAdjustment,
  }

  return (
    <h1 className="cinelibrary-wordmark" style={style}>
      <span className="cinelibrary-wordmark-main">Cine</span>
      <span className="cinelibrary-wordmark-accent">Library</span>
    </h1>
  )
}

interface TypographyPreviewPanelProps {
  selectedId: number
  isLoading: boolean
  error: string
  onSelect: (id: number) => void
  onPrevious: () => void
  onNext: () => void
  onApply: () => void
  onClose: () => void
}

export function TypographyPreviewPanel({
  selectedId,
  isLoading,
  error,
  onSelect,
  onPrevious,
  onNext,
  onApply,
  onClose,
}: TypographyPreviewPanelProps) {
  const selected = getTypographyVariant(selectedId)
  return (
    <section className="typography-preview-panel" aria-label="Подбор шрифта">
      <div className="typography-preview-heading">
        <div>
          <strong>Вариант {String(selected.id).padStart(2, '0')} / 20</strong>
          <p>{selected.name}</p>
        </div>
        <button type="button" className="typography-preview-close" onClick={onClose}>
          Закрыть
        </button>
      </div>

      <div className="typography-variant-grid">
        {TYPOGRAPHY_VARIANTS.map((variant) => (
          <button
            type="button"
            className={variant.id === selectedId ? 'is-active' : ''}
            aria-pressed={variant.id === selectedId}
            data-typography-variant
            data-typography-id={variant.id}
            key={variant.id}
            onClick={() => onSelect(variant.id)}
          >
            {String(variant.id).padStart(2, '0')}
          </button>
        ))}
      </div>

      <div className="typography-preview-actions">
        <button type="button" onClick={onPrevious}>← Предыдущий</button>
        <button type="button" onClick={onNext}>Следующий →</button>
        <button
          type="button"
          className="typography-apply-button"
          disabled={isLoading}
          onClick={onApply}
        >
          ✓ Применить вариант
        </button>
      </div>

      <div className="typography-preview-status" role="status" aria-live="polite">
        {isLoading ? 'Загружаем шрифты…' : error}
      </div>
    </section>
  )
}
