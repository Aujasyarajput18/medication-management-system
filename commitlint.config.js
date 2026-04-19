// Conventional commit enforcement
// Format: <type>(<scope>): <description>
// Types: feat | fix | docs | style | refactor | test | chore | security
// Scope: auth | medicines | doses | caregiver | pwa | i18n | security | ci | db
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore', 'security'],
    ],
    'scope-enum': [
      1,
      'always',
      ['auth', 'medicines', 'doses', 'caregiver', 'pwa', 'i18n', 'security', 'ci', 'db', 'ui', 'infra'],
    ],
    'subject-case': [2, 'never', ['start-case', 'pascal-case', 'upper-case']],
    'header-max-length': [2, 'always', 100],
  },
};
