/**
 * The package's version, read from pyproject.toml.
 *
 * `eleph.__version__` is read from installed package metadata rather than
 * written down a second time, for the reason CHANGELOG.md gives: a version
 * repeated in two files is a version that will eventually disagree with
 * itself, quietly. This site had a third copy and it did exactly that, showing
 * v0.3.0 in the header of every page after 0.4.0 shipped.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))

export function packageVersion() {
  const toml = fs.readFileSync(path.join(here, '..', '..', 'pyproject.toml'), 'utf8')
  const found = /^version\s*=\s*"([^"]+)"/m.exec(toml)
  if (!found) throw new Error('no version in pyproject.toml')
  return found[1]
}
