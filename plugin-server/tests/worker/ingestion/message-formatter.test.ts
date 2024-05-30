import { ISOTimestamp, PostIngestionEvent, Team } from '../../../src/types'
import { MessageFormatter, MessageFormatterOptions } from '../../../src/worker/ingestion/message-formatter'

type TestWebhookFormatterOptions = Partial<MessageFormatterOptions> & {
    personProperties?: PostIngestionEvent['person_properties']
}

describe('MessageFormatter', () => {
    const team = { id: 123, person_display_name_properties: null } as Team
    const event: PostIngestionEvent = {
        event: '$pageview',
        eventUuid: '123',
        teamId: 123,
        distinctId: 'WALL-E',
        person_properties: { email: 'test@posthog.com' },
        person_created_at: '2021-10-31T00%3A44%3A00.000Z' as ISOTimestamp,

        elementsList: [],
        properties: { $browser: 'Chrome' },
        timestamp: '2021-10-31T00%3A44%3A00.000Z' as ISOTimestamp,
        groups: {
            organization: {
                index: 1,
                type: 'organization',
                key: '123',
                properties: { name: 'PostHog', plan: 'paid' },
            },

            project: {
                index: 2,
                type: 'project',
                key: '234',
                properties: {},
            },
        },
    }

    const createFormatter = (options?: TestWebhookFormatterOptions) => {
        return new MessageFormatter({
            sourceName: options?.sourceName ?? 'action1',
            sourcePath: options?.sourcePath ?? '/action/1',
            event: {
                ...(options?.event ?? event),
                person_properties: options?.personProperties ?? event.person_properties,
            },
            team: options?.team ?? team,
            siteUrl: options?.siteUrl ?? 'http://localhost:8000',
        })
    }

    beforeEach(() => {
        process.env.NODE_ENV = 'test'
    })

    describe('webhook formatting options', () => {
        const cases: [string, TestWebhookFormatterOptions][] = [
            ['{{person}}', {}],
            ['{{person.link}}', {}],
            ['{{user.name}}', {}], // Alias for person name
            ['{{user.browser}}', {}], // Otherwise just alias to event properties
            ['{{action.name}}', {}],
            ['{{action.name}} was done by {{user.name}}', {}],
            ['{{source.name}}', {}],
            ['{{source.name}} was done by {{user.name}}', {}],
            // Handle escaping brackets
            ['{{action.name\\}} got done by \\{{user.name\\}}', {}],
            ['{{event}}', {}],
            ['{{event.uuid}}', {}],
            ['{{event.name}}', {}], // Alias for event name
            ['{{event.event}}', {}],
            ['{{event.distinct_id}}', {}],
            [
                '{{person}}',
                {
                    personProperties: {
                        imię: 'Grzegorz',
                        nazwisko: 'Brzęczyszczykiewicz',
                    },
                    team: { ...team, person_display_name_properties: ['nazwisko'] },
                },
            ],
            [
                '{{person.properties.enjoys_broccoli_on_pizza}}',
                {
                    personProperties: { enjoys_broccoli_on_pizza: false },
                },
            ],
            [
                '{{person.properties.pizza_ingredient_ranking}}',
                {
                    personProperties: { pizza_ingredient_ranking: ['pineapple', 'broccoli', 'aubergine'] },
                },
            ],
            ['{{user.missing_property}}', {}],
            ['{{event}}', { event: { ...event, eventUuid: '**)', event: 'text](yes!), [new link' } }], // Special escaping
            [
                '{{user.name}} from {{user.browser}} on {{event.properties.page_title}} page with {{event.properties.fruit}}, {{event.properties.with space}}',
                {
                    event: {
                        ...event,
                        distinctId: '2',
                        properties: { $browser: 'Chrome', page_title: 'Pricing', 'with space': 'yes sir' },
                    },
                },
            ],
            ['{{groups}}', {}],
            ['{{groups.missing}}', {}],
            ['{{groups.organization}}', {}],
            ['{{groups.organization.properties.plan}}', {}],
            ['{{groups.project}}', {}], // No-name one
            ['{ "event_properties": {{event.properties}}, "person_link": "{{person.link}}" }', {}], // JSON object
            ['{{ person.name}} did {{ event . event }}', {}], // Weird spacing
        ]

        it.each(cases)('%s %s', (template, options) => {
            const formatter = createFormatter(options)
            const message = formatter.format(template)
            // For non-slack messages the text is always markdown
            expect(message).toMatchSnapshot()
        })

        it('should handle an advanced case', () => {
            const formatter = createFormatter({
                event: {
                    properties: {
                        array_item: ['item1', 'item2'],
                        bad_string: '`"\'\\',
                    },
                },
            })
            const message = formatter.format(`{
    "event_properties": {{event.properties}},
    "string_with_complex_properties": "This is a string with {{event.properties.array_item}} and {{event.properties.bad_string}}"
}`)

            console.log(message)
            expect(message).toMatchSnapshot()

            const parsed = JSON.parse(message)

            expect(parsed).toMatchInlineSnapshot(`
                Object {
                  "event_properties": Object {
                    "array_item": Array [
                      "item1",
                      "item2",
                    ],
                    "bad_string": "\`\\"'\\\\",
                  },
                  "string_with_complex_properties": "This is a string with [\\"item1\\",\\"item2\\"] and \`\\"'\\\\",
                }
            `)
        })
    })
})