/**
 * Aujasya — Meal Anchor Time Hook
 * Converts meal anchors to human-readable time strings.
 */

const DEFAULT_MEAL_TIMES: Record<string, string> = {
  on_waking: '06:00',
  before_breakfast: '07:30',
  with_breakfast: '08:00',
  after_breakfast: '08:30',
  before_lunch: '12:30',
  with_lunch: '13:00',
  after_lunch: '13:30',
  before_dinner: '19:30',
  with_dinner: '20:00',
  after_dinner: '20:30',
  at_bedtime: '22:00',
  any_time: '',
};

export function useMealAnchorTime() {
  function getTimeForAnchor(anchor: string): string {
    return DEFAULT_MEAL_TIMES[anchor] || '';
  }

  function getDisplayName(anchor: string, locale: string = 'en'): string {
    const names: Record<string, Record<string, string>> = {
      en: {
        on_waking: 'On Waking',
        before_breakfast: 'Before Breakfast',
        with_breakfast: 'With Breakfast',
        after_breakfast: 'After Breakfast',
        before_lunch: 'Before Lunch',
        with_lunch: 'With Lunch',
        after_lunch: 'After Lunch',
        before_dinner: 'Before Dinner',
        with_dinner: 'With Dinner',
        after_dinner: 'After Dinner',
        at_bedtime: 'At Bedtime',
        any_time: 'Any Time',
      },
      hi: {
        on_waking: 'उठने पर',
        before_breakfast: 'नाश्ते से पहले',
        with_breakfast: 'नाश्ते के साथ',
        after_breakfast: 'नाश्ते के बाद',
        before_lunch: 'दोपहर के भोजन से पहले',
        with_lunch: 'दोपहर के भोजन के साथ',
        after_lunch: 'दोपहर के भोजन के बाद',
        before_dinner: 'रात के खाने से पहले',
        with_dinner: 'रात के खाने के साथ',
        after_dinner: 'रात के खाने के बाद',
        at_bedtime: 'सोने से पहले',
        any_time: 'कभी भी',
      },
    };

    return names[locale]?.[anchor] || names['en']?.[anchor] || anchor;
  }

  function formatTime12h(time24: string): string {
    if (!time24) return '';
    const [hours, minutes] = time24.split(':').map(Number);
    const period = hours >= 12 ? 'PM' : 'AM';
    const hours12 = hours % 12 || 12;
    return `${hours12}:${minutes.toString().padStart(2, '0')} ${period}`;
  }

  return { getTimeForAnchor, getDisplayName, formatTime12h };
}
