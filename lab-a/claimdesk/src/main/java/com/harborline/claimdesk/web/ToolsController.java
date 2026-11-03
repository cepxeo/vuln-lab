package com.harborline.claimdesk.web;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import org.thymeleaf.TemplateEngine;
import org.thymeleaf.context.Context;
import org.thymeleaf.templatemode.TemplateMode;
import org.thymeleaf.templateresolver.StringTemplateResolver;

import java.io.ByteArrayInputStream;
import java.io.ObjectInputStream;
import java.util.Base64;

@Controller
public class ToolsController {

    // Adjuster "notification preview": the supplied body is rendered through a
    // Thymeleaf string template, so an expression in the body is evaluated
    // server-side (template injection / SSTI).
    @GetMapping("/tools/preview")
    @ResponseBody
    public String preview(@RequestParam(defaultValue = "Hello [[${name}]]") String template) {
        TemplateEngine engine = new TemplateEngine();
        StringTemplateResolver r = new StringTemplateResolver();
        r.setTemplateMode(TemplateMode.TEXT);
        engine.setTemplateResolver(r);
        Context ctx = new Context();
        ctx.setVariable("name", "preview");
        return engine.process(template, ctx);
    }

    // "Recently viewed" restore: the rv cookie holds a base64 Java-serialized
    // object that is read back with ObjectInputStream (insecure deserialization;
    // commons-collections 3.2.1 is on the classpath).
    @GetMapping("/recent")
    @ResponseBody
    public String recent(@CookieValue(value = "rv", required = false) String rv) {
        if (rv == null) return "no recent items";
        try {
            byte[] data = Base64.getDecoder().decode(rv);
            ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(data));
            Object o = ois.readObject();
            return "restored: " + o;
        } catch (Exception e) {
            return "restore failed: " + e.getMessage();
        }
    }
}
