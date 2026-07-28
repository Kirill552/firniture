import { describe, expect, it } from "vitest"
import { facadeWidth, shelfOffsets, wallFit } from "./module-geometry"

describe("wallFit", () => {
  it("считает остаток под щелевую планку", () => {
    const fit = wallFit([600, 600, 600], 3000)
    expect(fit.modulesWidth).toBe(1800)
    expect(fit.remainder).toBe(1200)
    expect(fit.status).toBe("gap")
  })

  it("видит перелёт за габарит стены", () => {
    const fit = wallFit([900, 900, 900, 900], 3000)
    expect(fit.remainder).toBe(-600)
    expect(fit.status).toBe("overflow")
  })

  it("узнаёт точно заполненную стену", () => {
    expect(wallFit([1500, 1500], 3000).status).toBe("fits")
  })

  it("пустой заказ занимает нулевую ширину", () => {
    expect(wallFit([], 3000)).toEqual({ modulesWidth: 0, remainder: 3000, status: "gap" })
  })
})

describe("facadeWidth", () => {
  it("одна створка на корпус 600 при зазоре 4 — это 596", () => {
    expect(facadeWidth(600, 1, 4)).toBe(596)
  })

  it("две створки на корпус 600 — по 298", () => {
    expect(facadeWidth(600, 2, 4)).toBe(298)
  })

  it("без дверей ширины нет", () => {
    expect(facadeWidth(600, 0, 4)).toBe(0)
  })
})

describe("shelfOffsets", () => {
  it("одна полка делит проём пополам", () => {
    expect(shelfOffsets(700, 1)).toEqual([350])
  })

  it("три полки делят проём на четыре равные части", () => {
    expect(shelfOffsets(800, 3)).toEqual([200, 400, 600])
  })

  it("без полок пусто", () => {
    expect(shelfOffsets(700, 0)).toEqual([])
  })
})
