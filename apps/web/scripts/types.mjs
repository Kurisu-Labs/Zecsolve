import fs from 'node:fs/promises'
import openapiTS, { astToString } from 'openapi-typescript'

// Published backend schemas are usable without starting a database or API server.
const root = new URL('../../../contracts/', import.meta.url)
const schemas = {}
for (const file of (await fs.readdir(root)).filter((f) => f.endsWith('.schema.json')).sort()) {
  const name = file.replace('.schema.json', '').replace(/-([a-z])/g, (_, c) => c.toUpperCase())
  const schema = JSON.parse(await fs.readFile(new URL(file, root), 'utf8'))
  const rewritten = JSON.parse(JSON.stringify(schema).replaceAll('#/$defs/', `#/components/schemas/${name}_`))
  for (const [key, value] of Object.entries(rewritten.$defs ?? {})) schemas[`${name}_${key}`] = value
  delete rewritten.$defs
  schemas[name] = rewritten
}
const output = astToString(
  await openapiTS({
    openapi: '3.1.0',
    info: { title: 'Published Zecsolve contracts', version: '1' },
    paths: {},
    components: { schemas },
  }),
)
const path = new URL('../src/api/contracts.d.ts', import.meta.url)
if (process.argv.includes('--check')) {
  if ((await fs.readFile(path, 'utf8')).replaceAll('\r\n', '\n') !== output)
    throw new Error('Contract types drifted. Run npm run types:api.')
} else await fs.writeFile(path, output)
