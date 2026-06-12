import i18n from 'i18next';
import { useTranslation } from 'react-i18next';

const STORAGE_KEY = 'aerus_language';

export function LanguageSwitcher() {
  const { t } = useTranslation();
  const current = i18n.resolvedLanguage?.startsWith('pt') ? 'pt' : 'en';

  const setLanguage = (lang: 'pt' | 'en') => {
    if (lang === current) return;
    void i18n.changeLanguage(lang);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, lang);
    }
  };

  return (
    <div
      className='language-switcher'
      role='group'
      aria-label={t('common.language')}
    >
      <button
        type='button'
        className={current === 'pt' ? 'active' : ''}
        onClick={() => setLanguage('pt')}
        aria-pressed={current === 'pt'}
      >
        PT
      </button>
      <button
        type='button'
        className={current === 'en' ? 'active' : ''}
        onClick={() => setLanguage('en')}
        aria-pressed={current === 'en'}
      >
        EN
      </button>
    </div>
  );
}
