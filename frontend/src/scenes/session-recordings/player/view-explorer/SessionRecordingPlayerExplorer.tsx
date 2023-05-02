import { LemonButton, LemonTag } from '@posthog/lemon-ui'
import { useResizeObserver } from 'lib/hooks/useResizeObserver'
import { useState } from 'react'
import './SessionRecordingPlayerExplorer.scss'
import { LemonBanner } from 'lib/lemon-ui/LemonBanner'

export type SessionRecordingPlayerExplorerProps = {
    html: string
    width: number
    height: number
    onClose?: () => void
}

export function SessionRecordingPlayerExplorer({
    html,
    width,
    height,
    onClose,
}: SessionRecordingPlayerExplorerProps): JSX.Element | null {
    const [iframeKey, setIframeKey] = useState(0)
    const [noticeHidden, setNoticeHidden] = useState(false)

    const { ref: elementRef, height: wrapperHeight = height, width: wrapperWidth = width } = useResizeObserver()

    const scale = Math.min(wrapperWidth / width, wrapperHeight / height)

    return (
        <div className="SessionRecordingPlayerExplorer space-y-2">
            <div className="shrink-0 space-y-2">
                <div className="flex items-center gap-2">
                    <span className="flex-1 font-semibold">
                        View Explorer <LemonTag>Experimental</LemonTag>
                    </span>
                    <LemonButton type="secondary" onClick={() => setIframeKey(iframeKey + 1)}>
                        Reset
                    </LemonButton>
                    <LemonButton type="primary" onClick={onClose}>
                        Close
                    </LemonButton>
                </div>
                {!noticeHidden && (
                    <LemonBanner type="info" onClose={() => setNoticeHidden(true)}>
                        This is a snapshot of the screen that was recorded. It may not be 100% accurate, but should be
                        close enough to help you debug.
                        <br />
                        You can interact with the content below but most things won't work as it is only a snapshot of
                        your app. Use your Browser Developer Tools to inspect the content.
                    </LemonBanner>
                )}
            </div>

            <div className="SessionRecordingPlayerExplorer__wrapper" ref={elementRef}>
                <div className="SessionRecordingPlayerExplorer__transform">
                    <iframe
                        key={iframeKey}
                        srcDoc={html}
                        width={width}
                        height={height}
                        className="SessionRecordingPlayerExplorer__iframe ph-no-capture"
                        // eslint-disable-next-line react/forbid-dom-props
                        style={{ transform: `scale(${scale})` }}
                    />
                </div>
            </div>
        </div>
    )
}
