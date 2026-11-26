import { useRef, useState } from 'react'
import { DownloadDeliveryError, requestMoviesByTmdb, type MovieView } from '../data/movieApi'
import type { RecommendationResponse, TemporaryRecommendation } from '../data/recommendationApi'

const MAX_DOWNLOAD_SELECTION = 5

interface Props {
  result: RecommendationResponse
  requestedCount: number
  knownMovies: MovieView[]
  onBack: () => void
  onDelivered: (tmdbIds: number[]) => void
}

function FitBreakdown({ recommendation }: { recommendation: TemporaryRecommendation }) {
  const { breakdown, suggestion } = recommendation
  return (
    <div className="recommendation-fit">
      <h4>Почему подходит</h4>
      {breakdown ? (
        <>
          <dl className="recommendation-fit-rows">
            {breakdown.matches.map(({ label, score, detail }, index) => {
              const band = score === null ? 'unknown' : score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low'
              const verdict = { unknown: 'Нет данных', high: 'Высокое', medium: 'Частичное', low: 'Слабое' }[band]
              return (
                <div className="recommendation-fit-row" key={`${label}-${index}`}>
                  <dt>{label}</dt>
                  <dd>
                    <div className={`recommendation-fit-track is-${band}`} aria-hidden="true">
                      {score !== null && <span style={{ width: `${score}%` }} />}
                    </div>
                    <span className="recommendation-fit-value">
                      {score === null ? verdict : `${score} из 100 · ${verdict}`}
                    </span>
                    {detail && <p>{detail}</p>}
                  </dd>
                </div>
              )
            })}
          </dl>
          <div className="recommendation-fit-total">
            <strong>
              {breakdown.chefPick ? 'По пожеланиям' : 'Итог'} · {suggestion.relevance} из 100
            </strong>
            {breakdown.wishScore !== null && breakdown.referenceScore !== null && (
              <span>
                Пожелания {breakdown.wishScore} × 60% · Ориентиры {breakdown.referenceScore} × 40%
              </span>
            )}
            {breakdown.summary && <p>{breakdown.summary}</p>}
          </div>
        </>
      ) : (
        <>
          <p>{recommendation.scoreExplanation || suggestion.reason}</p>
          <strong>Итог · {suggestion.relevance} из 100</strong>
        </>
      )}
    </div>
  )
}

export function RecommendationResults({ result, requestedCount, knownMovies, onBack, onDelivered }: Props) {
  const [selected, setSelected] = useState<number[]>([])
  const [isSending, setIsSending] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const sending = useRef(false)
  const ranked = result.movies.filter((item) => !item.breakdown?.chefPick)
  const chefPicks = result.movies.filter((item) => item.breakdown?.chefPick)

  const requestId = (item: TemporaryRecommendation) =>
    item.tmdbId ?? item.movie?.tmdbId ?? knownMovies.find((movie) => movie.id === item.existingMovieId)?.tmdbId

  const canRequest = (item: TemporaryRecommendation) =>
    (item.status === 'draft_ready' || item.status === 'already_exists')
    && requestId(item) != null
    && item.canRequestDownload !== false
    && !knownMovies.some((movie) => movie.id === item.existingMovieId && movie.availability === 'available')

  const send = async (ids: number[]) => {
    if (sending.current || !ids.length || ids.length > MAX_DOWNLOAD_SELECTION) return
    sending.current = true
    setIsSending(true)
    setNotice('')
    setError('')
    try {
      const delivered = await requestMoviesByTmdb(ids, { preferPosters: true })
      onDelivered(delivered.map(({ downloadRequest }) => downloadRequest.tmdbMovieId))
      setSelected((current) => current.filter((id) => !ids.includes(id)))
      setNotice(ids.length === 1 ? 'Заявка отправлена в Telegram.' : `Заявка на ${ids.length} фильмов отправлена в Telegram.`)
    } catch (cause) {
      if (cause instanceof DownloadDeliveryError && cause.deliveredTmdbIds.length) {
        const delivered = cause.deliveredTmdbIds
        onDelivered(delivered)
        setSelected((current) => current.filter((id) => !delivered.includes(id)))
      }
      setError(cause instanceof Error ? cause.message : 'Не удалось отправить заявку.')
    } finally {
      sending.current = false
      setIsSending(false)
    }
  }

  const renderCard = (recommendation: TemporaryRecommendation) => {
    const localMovie = knownMovies.find((movie) => movie.id === recommendation.existingMovieId)
    const { suggestion, movie, id } = recommendation
    const poster = movie?.posterUrl ?? localMovie?.poster
    const year = movie?.releaseYear ?? localMovie?.year ?? suggestion.releaseYear
    const overview = movie?.overview ?? localMovie?.overview
    const genres = movie?.genres.map((genre) => genre.displayName) ?? localMovie?.genres ?? []
    const tmdbId = requestId(recommendation)
    const checked = tmdbId != null && selected.includes(tmdbId)
    return (
      <article key={id}>
        {poster ? <img src={poster} alt={suggestion.title} /> : <div className="temporary-poster-fallback">Нет постера</div>}
        <div className="temporary-recommendation-body">
          <div className="temporary-recommendation-heading">
            <div>
              <h3>{suggestion.title}</h3>
              <p>{year || 'Год неизвестен'}{genres.length > 0 && ` · ${genres.join(', ')}`}</p>
            </div>
            {tmdbId != null && canRequest(recommendation) && (
              <label className="recommendation-select-movie">
                <input
                  type="checkbox"
                  aria-label={`Выбрать ${suggestion.title}`}
                  checked={checked}
                  disabled={isSending || (!checked && selected.length >= MAX_DOWNLOAD_SELECTION)}
                  onChange={(event) => {
                    const select = event.target.checked
                    setSelected((current) => {
                      if (!select) return current.filter((value) => value !== tmdbId)
                      if (current.length >= MAX_DOWNLOAD_SELECTION || current.includes(tmdbId)) return current
                      return [...current, tmdbId]
                    })
                  }}
                />
                Выбрать
              </label>
            )}
          </div>
          <FitBreakdown recommendation={recommendation} />
          {overview && <p>{overview}</p>}
          {recommendation.people.length > 0 && (
            <p className="temporary-people">{recommendation.people.slice(0, 8).map((person) => person.displayName).join(', ')}</p>
          )}
          {recommendation.issues.length > 0 && <p className="temporary-issues">{recommendation.issues.join(' ')}</p>}
        </div>
      </article>
    )
  }

  return (
    <div className="recommendation-result-layout">
      {result.movies.length < requestedCount && <p>Подтверждено фильмов: {result.movies.length} из {requestedCount}.</p>}
      {ranked.length > 0 && (
        <section className="temporary-recommendations" aria-label="Основной рейтинг">
          {chefPicks.length > 0 && <h3>Основной рейтинг</h3>}
          {ranked.map(renderCard)}
        </section>
      )}
      {chefPicks.length > 0 && (
        <section className="temporary-recommendations recommendation-chef" aria-labelledby="chef-picks-title">
          <h3 id="chef-picks-title">Блюдо от шефа!</h3>
          <p>Подходят под запрос. Для сравнения с ориентирами не хватило данных.</p>
          {chefPicks.map(renderCard)}
        </section>
      )}
      {(notice || error) && (
        <div className="recommendation-download-feedback">
          {notice && <p role="status">{notice}</p>}
          {error && <p className="configurator-error" role="alert">{error}</p>}
        </div>
      )}
      <div className="configurator-actions">
        <button type="button" className="configurator-secondary" disabled={isSending} onClick={onBack}>
          Вернуться к сводке
        </button>
        {result.movies.some(canRequest) && (
          <button type="button" className="configurator-primary" disabled={isSending || selected.length === 0} onClick={() => void send(selected)}>
            {isSending ? 'Отправляем…' : `Запросить загрузку · ${selected.length} из ${MAX_DOWNLOAD_SELECTION}`}
          </button>
        )}
      </div>
    </div>
  )
}
