/** @odoo-module **/

// noinspection JSUnusedGlobalSymbols
export async function resizeImage(file, maxWidth, maxHeight) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = (e) => {
            const image = new Image()
            image.onload = () => {
                const scale = Math.min(maxWidth / image.width, maxHeight / image.height, 1)
                const width = image.width * scale
                const height = image.height * scale

                const canvas = document.createElement('canvas')
                canvas.width = width
                canvas.height = height

                const ctx = canvas.getContext('2d')
                ctx.drawImage(image, 0, 0, width, height)

                resolve(canvas.toDataURL(file.type, 0.8).split(',')[1])
            }
            image.onerror = (error) => reject(error)
            image.src = e.target.result
        }
        reader.onerror = (error) => reject(error)
        reader.readAsDataURL(file)
    })
}

// noinspection JSUnusedGlobalSymbols
export async function blobToBase(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}