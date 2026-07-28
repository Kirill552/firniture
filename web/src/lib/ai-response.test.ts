import { describe, expect, it } from 'vitest';
import { parseAiResponse } from './ai-response';

describe('parseAiResponse', () => {
  it('extracts buttons from a multiline marker', () => {
    expect(parseAiResponse('Выберите тип:\n[BUTTONS: "Навесной шкаф",\n"Пенал"]')).toEqual({
      cleanText: 'Выберите тип:',
      buttons: ['Навесной шкаф', 'Пенал'],
    });
  });

  it('extracts multiple button markers', () => {
    expect(parseAiResponse('Первый выбор [BUTTONS: "Да", "Нет"]\nВторой [BUTTONS: "Позже"]')).toEqual({
      cleanText: 'Первый выбор\nВторой',
      buttons: ['Да', 'Нет', 'Позже'],
    });
  });

  it('removes an unfinished reasoning block', () => {
    expect(parseAiResponse('Готовый ответ<think>внутреннее рассуждение')).toEqual({
      cleanText: 'Готовый ответ',
      buttons: [],
    });
  });

  it('removes service markers and only technical Latin codes in labels', () => {
    expect(parseAiResponse('Выберите материал [TOOL_CALL: find]\nfunction_call: lookup\n[BUTTONS: "Навесной шкаф (wall)", "ЛДСП (16 мм)", "ПВХ 2 мм"]')).toEqual({
      cleanText: 'Выберите материал',
      buttons: ['Навесной шкаф', 'ЛДСП (16 мм)', 'ПВХ 2 мм'],
    });
  });

  it('keeps ordinary text unchanged', () => {
    expect(parseAiResponse('Оставьте этот текст без изменений.')).toEqual({
      cleanText: 'Оставьте этот текст без изменений.',
      buttons: [],
    });
  });

  it('parses the production screenshot response into Russian buttons', () => {
    expect(parseAiResponse('Начнём с типа корпуса. Что рассчитываем? [BUTTONS: "Навесной шкаф (wall)", "Напольная тумба (base)", "Тумба под мойку (base_sink)", "Тумба с ящиками (drawer)", "Пенал (tall)"]')).toEqual({
      cleanText: 'Начнём с типа корпуса. Что рассчитываем?',
      buttons: ['Навесной шкаф', 'Напольная тумба', 'Тумба под мойку', 'Тумба с ящиками', 'Пенал'],
    });
  });
});

describe('подписи кнопок с запятой', () => {
  it('не разрезает подпись по запятой внутри кавычек', () => {
    // Живой случай с прода: получилось четыре кнопки «Да», «нужны ручки»,
    // «Нет», «ручки не нужны» вместо двух осмысленных.
    const result = parseAiResponse(
      'Нужны ли ручки на фасаде?\n[BUTTONS: "Да, нужны ручки", "Нет, ручки не нужны"]'
    );
    expect(result.buttons).toEqual(['Да, нужны ручки', 'Нет, ручки не нужны']);
    expect(result.cleanText).toBe('Нужны ли ручки на фасаде?');
  });

  it('без кавычек по-прежнему делит по запятой', () => {
    const result = parseAiResponse('Что выберем?\n[BUTTONS: ЛДСП, МДФ, Массив]');
    expect(result.buttons).toEqual(['ЛДСП', 'МДФ', 'Массив']);
  });
});
