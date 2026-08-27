/** Facts about the project that appear in more than one place. */
export const site = {
  name: 'eleph',
  tagline: 'A language whose programs cannot lie.',
  description:
    'Speech acts, a history that is the only state, and correctness conditions derived from the program text rather than written beside it.',
  version: '0.3.0',
  author: 'Isaac Mello',
  repo: 'https://github.com/dev-isaacmello/eleph',
  issues: 'https://github.com/dev-isaacmello/eleph/issues',
  pypi: 'https://pypi.org/project/eleph/',
  paper: 'http://www-formal.stanford.edu/jmc/elephant.html',
  taubench: 'https://arxiv.org/abs/2406.12045',
  license: 'MIT',
} as const

/** Deep links into the repository, so the docs never transcribe a path. */
export const source = {
  file: (p: string) => `${site.repo}/blob/main/${p}`,
  tree: (p: string) => `${site.repo}/tree/main/${p}`,
} as const
