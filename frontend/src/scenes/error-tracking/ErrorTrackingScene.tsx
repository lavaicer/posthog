import { LemonSegmentedButton } from '@posthog/lemon-ui'
import { useActions, useValues } from 'kea'
import { LemonTableLink } from 'lib/lemon-ui/LemonTable/LemonTableLink'
import { useMemo } from 'react'
import { SceneExport } from 'scenes/sceneTypes'
import { urls } from 'scenes/urls'

import { Query } from '~/queries/Query/Query'
import { QueryContext, QueryContextColumnComponent, QueryContextColumnTitleComponent } from '~/queries/types'

import { ErrorTrackingFilters } from './ErrorTrackingFilters'
import { errorTrackingLogic } from './errorTrackingLogic'
import { errorTrackingSceneLogic } from './errorTrackingSceneLogic'
import { errorTrackingQuery } from './queries'

export const scene: SceneExport = {
    component: ErrorTrackingScene,
    logic: errorTrackingSceneLogic,
}

export function ErrorTrackingScene(): JSX.Element {
    const { order } = useValues(errorTrackingSceneLogic)
    const { dateRange, filterTestAccounts, filterGroup, sparklineSelection } = useValues(errorTrackingLogic)

    const { period, multiplier, unit } = sparklineSelection

    const query = useMemo(
        () => errorTrackingQuery({ order, dateRange, filterTestAccounts, filterGroup, period, multiplier, unit }),
        [order, dateRange, filterTestAccounts, filterGroup, period, multiplier, unit]
    )

    const context: QueryContext = {
        columns: {
            error: {
                width: '50%',
                render: CustomGroupTitleColumn,
            },
            volume: { renderTitle: CustomVolumeColumnHeader },
        },
        showOpenEditorButton: false,
    }

    return (
        <div className="space-y-4">
            <ErrorTrackingFilters />
            <Query query={query} context={context} />
        </div>
    )
}

const CustomVolumeColumnHeader: QueryContextColumnTitleComponent = ({ columnName }) => {
    const { sparklineSelection, sparklineOptions: options } = useValues(errorTrackingLogic)
    const { setSparklineSelection } = useActions(errorTrackingLogic)

    return (
        <div className="flex justify-between items-center min-w-64">
            <div>{columnName}</div>
            <LemonSegmentedButton
                size="xsmall"
                value={sparklineSelection.value}
                options={options}
                onChange={(value) => {
                    setSparklineSelection(options.find((o) => o.value === value))
                }}
            />
        </div>
    )
}

const CustomGroupTitleColumn: QueryContextColumnComponent = (props) => {
    const { value } = props
    const properties = JSON.parse(value as string)

    return (
        <LemonTableLink
            title={properties.$exception_type}
            description={<div className="line-clamp-1">{properties.$exception_message}</div>}
            to={urls.errorTrackingGroup(properties.$exception_type)}
        />
    )
}
