package org.docfit.docx4j;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Enumeration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeSet;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import org.docx4j.openpackaging.packages.WordprocessingMLPackage;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NamedNodeMap;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.SAXException;

public final class Docx4jInspect {
    private static final String REL_NS =
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
    private static final String PACKAGE_REL_NS =
        "http://schemas.openxmlformats.org/package/2006/relationships";

    private Docx4jInspect() {}

    public static void main(String[] args) throws Exception {
        CliArgs parsed = parseArgs(args);
        Map<String, Object> report = inspect(parsed.input);
        Files.createDirectories(parsed.output.getParent());
        Files.writeString(parsed.output, toJson(report) + "\n", StandardCharsets.UTF_8);
    }

    private static CliArgs parseArgs(String[] args) {
        Path input = null;
        Path output = null;
        for (int index = 0; index < args.length; index++) {
            String arg = args[index];
            if ("--out".equals(arg)) {
                if (index + 1 >= args.length) {
                    throw new IllegalArgumentException("--out requires a path");
                }
                output = Paths.get(args[++index]);
            } else if (input == null) {
                input = Paths.get(arg);
            } else {
                throw new IllegalArgumentException("unexpected argument: " + arg);
            }
        }
        if (input == null || output == null) {
            throw new IllegalArgumentException("usage: Docx4jInspect input.docx --out report.json");
        }
        return new CliArgs(input, output);
    }

    private static Map<String, Object> inspect(Path input) throws Exception {
        Map<String, Object> report = orderedMap();
        Map<String, Object> data = emptyData();
        report.put("artifact_type", "docx4j_inspection");
        report.put("artifact_version", "1.0");
        report.put("producer", producer());
        report.put("created_at", OffsetDateTime.now(ZoneOffset.UTC).toString());
        report.put("input_docx", input.toString());
        report.put("input_exists", Files.exists(input));
        report.put("input_hashes", inputHashes(input));
        report.put("source_kind", "docx4j_sidecar_inspection");
        Map<String, Object> metadata = orderedMap();
        metadata.put("docx4j_version", "11.5.14");
        metadata.put("loaded_with_docx4j", false);
        metadata.put("docx4j_part_count", 0);
        report.put("metadata", metadata);
        report.put("data", data);
        if (!Files.exists(input)) {
            report.put("input_valid_docx", false);
            return report;
        }

        try {
            WordprocessingMLPackage wordPackage = WordprocessingMLPackage.load(input.toFile());
            metadata.put("loaded_with_docx4j", true);
            metadata.put("docx4j_part_count", wordPackage.getParts().getParts().size());
        } catch (Exception exc) {
            metadata.put("docx4j_load_error", exc.getClass().getName() + ": " + exc.getMessage());
        }

        try (ZipFile zip = new ZipFile(input.toFile())) {
            TreeSet<String> names = zipNames(zip);
            boolean validPackage =
                names.contains("[Content_Types].xml") && names.contains("word/document.xml");
            report.put("input_valid_docx", validPackage);
            data.put("package_parts", new ArrayList<>(names));
            if (!validPackage) {
                return report;
            }
            inspectDocumentXml(zip, data);
            inspectHeadersFooters(zip, names, data);
            inspectFootnotes(zip, names, data);
            inspectAllWordXmlParts(zip, names, data);
            inspectNumbering(zip, names, data);
        }
        return report;
    }

    private static Map<String, Object> emptyData() {
        Map<String, Object> data = orderedMap();
        data.put("paragraphs", new ArrayList<Map<String, Object>>());
        data.put("tables", new ArrayList<Map<String, Object>>());
        data.put("headers_footers", new ArrayList<Map<String, Object>>());
        data.put("fields", new ArrayList<Map<String, Object>>());
        data.put("footnotes", new ArrayList<Map<String, Object>>());
        data.put("text_boxes", new ArrayList<Map<String, Object>>());
        data.put("images", new ArrayList<Map<String, Object>>());
        data.put("breaks", new ArrayList<Map<String, Object>>());
        data.put("sections", new ArrayList<Map<String, Object>>());
        data.put("numbering_refs", new ArrayList<Map<String, Object>>());
        data.put("numbering_definitions", new ArrayList<Map<String, Object>>());
        data.put("unknown_visible_objects", new ArrayList<Map<String, Object>>());
        return data;
    }

    @SuppressWarnings("unchecked")
    private static void inspectDocumentXml(ZipFile zip, Map<String, Object> data)
        throws Exception {
        Document document = parseXml(zip, "word/document.xml");
        Element body = firstDescendant(document.getDocumentElement(), "body");
        if (body == null) {
            return;
        }
        List<Map<String, Object>> paragraphs = (List<Map<String, Object>>) data.get("paragraphs");
        List<Map<String, Object>> tables = (List<Map<String, Object>>) data.get("tables");
        int paragraphIndex = 0;
        int tableIndex = 0;
        for (Element child : elementChildren(body)) {
            String local = localName(child);
            if ("p".equals(local)) {
                paragraphIndex++;
                Map<String, Object> paragraph =
                    paragraphItem(child, "word/document.xml:p[" + paragraphIndex + "]", paragraphIndex);
                if (!isBlank((String) paragraph.get("text"))) {
                    paragraphs.add(paragraph);
                }
                collectNumberingRef(child, "word/document.xml:p[" + paragraphIndex + "]", data);
            } else if ("tbl".equals(local)) {
                tableIndex++;
                tables.add(tableItem(child, tableIndex));
            }
        }
        collectSections(document.getDocumentElement(), "word/document.xml", data);
    }

    @SuppressWarnings("unchecked")
    private static void inspectHeadersFooters(
        ZipFile zip,
        TreeSet<String> names,
        Map<String, Object> data
    ) throws Exception {
        List<Map<String, Object>> headersFooters =
            (List<Map<String, Object>>) data.get("headers_footers");
        for (String name : names) {
            if (!isHeaderFooterPart(name)) {
                continue;
            }
            Document document = parseXml(zip, name);
            String text = visibleText(document.getDocumentElement());
            if (isBlank(text)) {
                continue;
            }
            Map<String, Object> item = orderedMap();
            item.put("kind", name.contains("/header") ? "header" : "footer");
            item.put("part_name", name);
            item.put("text", text);
            item.put("source_ref", name + ":text");
            headersFooters.add(item);
        }
    }

    @SuppressWarnings("unchecked")
    private static void inspectFootnotes(
        ZipFile zip,
        TreeSet<String> names,
        Map<String, Object> data
    ) throws Exception {
        if (!names.contains("word/footnotes.xml")) {
            return;
        }
        List<Map<String, Object>> footnotes = (List<Map<String, Object>>) data.get("footnotes");
        Document document = parseXml(zip, "word/footnotes.xml");
        int index = 0;
        for (Element footnote : descendants(document.getDocumentElement(), "footnote")) {
            String text = visibleText(footnote);
            if (isBlank(text)) {
                continue;
            }
            index++;
            Map<String, Object> item = orderedMap();
            item.put("index", index);
            item.put("id", attributeByLocalName(footnote, "id"));
            item.put("text", text);
            item.put("source_ref", "word/footnotes.xml:footnote[" + index + "]");
            footnotes.add(item);
        }
    }

    private static void inspectAllWordXmlParts(
        ZipFile zip,
        TreeSet<String> names,
        Map<String, Object> data
    ) throws Exception {
        for (String name : names) {
            if (!name.startsWith("word/") || !name.endsWith(".xml")) {
                continue;
            }
            Document document;
            try {
                document = parseXml(zip, name);
            } catch (Exception exc) {
                addUnknown(data, "unparseable_xml_part", name, exc.getMessage());
                continue;
            }
            collectFields(document.getDocumentElement(), name, data);
            collectTextBoxes(document.getDocumentElement(), name, data);
            collectImages(zip, names, document.getDocumentElement(), name, data);
            collectBreaks(document.getDocumentElement(), name, data);
            if (!"word/document.xml".equals(name)) {
                collectSections(document.getDocumentElement(), name, data);
            }
            collectUnknownObjects(document.getDocumentElement(), name, data);
        }
    }

    @SuppressWarnings("unchecked")
    private static void inspectNumbering(
        ZipFile zip,
        TreeSet<String> names,
        Map<String, Object> data
    ) throws Exception {
        if (!names.contains("word/numbering.xml")) {
            return;
        }
        List<Map<String, Object>> definitions =
            (List<Map<String, Object>>) data.get("numbering_definitions");
        Document document = parseXml(zip, "word/numbering.xml");
        for (Element num : descendants(document.getDocumentElement(), "num")) {
            Map<String, Object> item = orderedMap();
            item.put("kind", "num");
            item.put("num_id", attributeByLocalName(num, "numId"));
            item.put("source_ref", "word/numbering.xml:num");
            definitions.add(item);
        }
        for (Element abstractNum : descendants(document.getDocumentElement(), "abstractNum")) {
            Map<String, Object> item = orderedMap();
            item.put("kind", "abstractNum");
            item.put("abstract_num_id", attributeByLocalName(abstractNum, "abstractNumId"));
            item.put("source_ref", "word/numbering.xml:abstractNum");
            definitions.add(item);
        }
    }

    private static Map<String, Object> paragraphItem(Element paragraph, String sourceRef, int index) {
        Map<String, Object> item = orderedMap();
        item.put("index", index);
        item.put("text", visibleText(paragraph));
        item.put("style", paragraphStyle(paragraph));
        item.put("style_details", paragraphStyleDetails(paragraph));
        item.put("source_ref", sourceRef);
        return item;
    }

    private static Map<String, Object> tableItem(Element table, int tableIndex) {
        Map<String, Object> item = orderedMap();
        List<Map<String, Object>> cells = new ArrayList<>();
        int rowIndex = 0;
        int globalCellIndex = 0;
        for (Element row : elementChildrenByLocalName(table, "tr")) {
            rowIndex++;
            int columnIndex = 0;
            for (Element cell : elementChildrenByLocalName(row, "tc")) {
                columnIndex++;
                globalCellIndex++;
                Map<String, Object> cellItem = orderedMap();
                cellItem.put("row", rowIndex);
                cellItem.put("column", columnIndex);
                cellItem.put("global_index", globalCellIndex);
                cellItem.put("text", visibleText(cell));
                cellItem.put(
                    "source_ref",
                    "word/document.xml:tbl[" + tableIndex + "]/tr[" + rowIndex + "]/tc[" + columnIndex + "]"
                );
                cells.add(cellItem);
            }
        }
        item.put("index", tableIndex);
        item.put("row_count", rowIndex);
        item.put("column_count", maxColumnCount(cells));
        item.put("cells", cells);
        item.put("source_ref", "word/document.xml:tbl[" + tableIndex + "]");
        return item;
    }

    @SuppressWarnings("unchecked")
    private static void collectNumberingRef(Element paragraph, String sourceRef, Map<String, Object> data) {
        Element numPr = firstDescendant(paragraph, "numPr");
        if (numPr == null) {
            return;
        }
        List<Map<String, Object>> refs = (List<Map<String, Object>>) data.get("numbering_refs");
        Map<String, Object> item = orderedMap();
        item.put("source_ref", sourceRef + "/numPr");
        Element numId = firstDescendant(numPr, "numId");
        Element ilvl = firstDescendant(numPr, "ilvl");
        item.put("num_id", numId == null ? "" : attributeByLocalName(numId, "val"));
        item.put("level", ilvl == null ? "" : attributeByLocalName(ilvl, "val"));
        refs.add(item);
    }

    @SuppressWarnings("unchecked")
    private static void collectFields(Element root, String partName, Map<String, Object> data) {
        List<Map<String, Object>> fields = (List<Map<String, Object>>) data.get("fields");
        int index = 0;
        for (Element instrText : descendants(root, "instrText")) {
            String text = textContent(instrText);
            if (isBlank(text)) {
                continue;
            }
            index++;
            Map<String, Object> item = orderedMap();
            item.put("kind", "instrText");
            item.put("text", text);
            item.put("source_ref", partName + ":instrText[" + index + "]");
            fields.add(item);
        }
        for (Element fldChar : descendants(root, "fldChar")) {
            index++;
            Map<String, Object> item = orderedMap();
            item.put("kind", "fldChar");
            item.put("field_char_type", attributeByLocalName(fldChar, "fldCharType"));
            item.put("source_ref", partName + ":fldChar[" + index + "]");
            fields.add(item);
        }
    }

    @SuppressWarnings("unchecked")
    private static void collectTextBoxes(Element root, String partName, Map<String, Object> data) {
        List<Map<String, Object>> textBoxes = (List<Map<String, Object>>) data.get("text_boxes");
        int index = 0;
        for (Element textBox : descendants(root, "txbxContent")) {
            String text = visibleText(textBox);
            if (isBlank(text)) {
                continue;
            }
            index++;
            Map<String, Object> item = orderedMap();
            item.put("index", index);
            item.put("text", text);
            item.put("source_ref", partName + ":txbxContent[" + index + "]");
            textBoxes.add(item);
        }
    }

    @SuppressWarnings("unchecked")
    private static void collectImages(
        ZipFile zip,
        TreeSet<String> names,
        Element root,
        String partName,
        Map<String, Object> data
    ) throws IOException {
        List<Map<String, Object>> images = (List<Map<String, Object>>) data.get("images");
        Map<String, String> relationships = readRelationships(zip, relationshipPartName(partName));
        int index = 0;
        for (Element blip : descendants(root, "blip")) {
            String relId = blip.getAttributeNS(REL_NS, "embed");
            if (relId == null || relId.isEmpty()) {
                relId = blip.getAttributeNS(REL_NS, "link");
            }
            if (relId == null || relId.isEmpty()) {
                continue;
            }
            index++;
            String target = relationships.getOrDefault(relId, "");
            String normalizedTarget = normalizeTarget(partName, target);
            Map<String, Object> item = orderedMap();
            item.put("index", index);
            item.put("relationship_id", relId);
            item.put("target", normalizedTarget);
            item.put("source_ref", partName + ":drawing[" + index + "]");
            if (names.contains(normalizedTarget)) {
                item.put("content_hash", sha256(zip, normalizedTarget));
            }
            images.add(item);
        }
    }

    @SuppressWarnings("unchecked")
    private static void collectBreaks(Element root, String partName, Map<String, Object> data) {
        List<Map<String, Object>> breaks = (List<Map<String, Object>>) data.get("breaks");
        int index = 0;
        for (Element br : descendants(root, "br")) {
            index++;
            Map<String, Object> item = orderedMap();
            item.put("type", attributeByLocalName(br, "type"));
            item.put("source_ref", partName + ":br[" + index + "]");
            breaks.add(item);
        }
    }

    @SuppressWarnings("unchecked")
    private static void collectSections(Element root, String partName, Map<String, Object> data) {
        List<Map<String, Object>> sections = (List<Map<String, Object>>) data.get("sections");
        int index = 0;
        for (Element sectPr : descendants(root, "sectPr")) {
            index++;
            Map<String, Object> item = orderedMap();
            item.put("source_ref", partName + ":sectPr[" + index + "]");
            Element pgSz = firstDescendant(sectPr, "pgSz");
            Element pgMar = firstDescendant(sectPr, "pgMar");
            if (pgSz != null) {
                item.put("page_size", attributesByLocalName(pgSz));
            }
            if (pgMar != null) {
                item.put("page_margin", attributesByLocalName(pgMar));
            }
            sections.add(item);
        }
    }

    private static void collectUnknownObjects(Element root, String partName, Map<String, Object> data) {
        int index = 0;
        for (Element object : descendants(root, "object")) {
            index++;
            addUnknown(data, "embedded_object", partName + ":object[" + index + "]", "embedded object");
        }
        index = 0;
        for (Element alternateContent : descendants(root, "AlternateContent")) {
            index++;
            addUnknown(
                data,
                "alternate_content",
                partName + ":AlternateContent[" + index + "]",
                "markup compatibility alternate content"
            );
        }
    }

    @SuppressWarnings("unchecked")
    private static void addUnknown(
        Map<String, Object> data,
        String objectType,
        String sourceRef,
        String reason
    ) {
        List<Map<String, Object>> unknown =
            (List<Map<String, Object>>) data.get("unknown_visible_objects");
        Map<String, Object> item = orderedMap();
        item.put("kind", "unknown_visible_object");
        item.put("object_type", objectType);
        item.put("source_ref", sourceRef);
        item.put("reason", reason == null ? "" : reason);
        item.put("blocking_candidate", true);
        unknown.add(item);
    }

    private static Map<String, String> readRelationships(ZipFile zip, String relPartName)
        throws IOException {
        ZipEntry entry = zip.getEntry(relPartName);
        if (entry == null) {
            return Collections.emptyMap();
        }
        try {
            Document document = parseXml(zip, relPartName);
            Map<String, String> relationships = new LinkedHashMap<>();
            for (Element relationship : descendants(document.getDocumentElement(), "Relationship")) {
                String id = relationship.getAttribute("Id");
                String target = relationship.getAttribute("Target");
                if (!id.isEmpty() && !target.isEmpty()) {
                    relationships.put(id, target);
                }
            }
            return relationships;
        } catch (Exception exc) {
            return Collections.emptyMap();
        }
    }

    private static String relationshipPartName(String partName) {
        int slash = partName.lastIndexOf('/');
        String dir = slash >= 0 ? partName.substring(0, slash) : "";
        String file = slash >= 0 ? partName.substring(slash + 1) : partName;
        return dir + "/_rels/" + file + ".rels";
    }

    private static String normalizeTarget(String sourcePartName, String target) {
        if (target == null || target.isEmpty()) {
            return "";
        }
        if (target.startsWith("/")) {
            return target.substring(1);
        }
        int slash = sourcePartName.lastIndexOf('/');
        String dir = slash >= 0 ? sourcePartName.substring(0, slash) : "";
        return Paths.get(dir).resolve(target).normalize().toString().replace('\\', '/');
    }

    private static Document parseXml(ZipFile zip, String name)
        throws IOException, ParserConfigurationException, SAXException {
        ZipEntry entry = zip.getEntry(name);
        if (entry == null) {
            throw new IOException("missing package part: " + name);
        }
        byte[] payload = zip.getInputStream(entry).readAllBytes();
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        DocumentBuilder builder = factory.newDocumentBuilder();
        return builder.parse(new ByteArrayInputStream(payload));
    }

    private static TreeSet<String> zipNames(ZipFile zip) {
        TreeSet<String> names = new TreeSet<>();
        Enumeration<? extends ZipEntry> entries = zip.entries();
        while (entries.hasMoreElements()) {
            ZipEntry entry = entries.nextElement();
            if (!entry.isDirectory()) {
                names.add(entry.getName());
            }
        }
        return names;
    }

    private static String visibleText(Element element) {
        List<String> parts = new ArrayList<>();
        for (Element text : descendants(element, "t")) {
            String value = textContent(text);
            if (!isBlank(value)) {
                parts.add(value.trim());
            }
        }
        return String.join("", parts).trim();
    }

    private static String textContent(Element element) {
        return element.getTextContent() == null ? "" : element.getTextContent();
    }

    private static String paragraphStyle(Element paragraph) {
        Element pPr = firstElementChildByLocalName(paragraph, "pPr");
        if (pPr == null) {
            return "";
        }
        Element pStyle = firstElementChildByLocalName(pPr, "pStyle");
        if (pStyle == null) {
            return "";
        }
        return attributeByLocalName(pStyle, "val");
    }

    private static Map<String, Object> paragraphStyleDetails(Element paragraph) {
        Map<String, Object> details = orderedMap();
        String style = paragraphStyle(paragraph);
        if (!style.isEmpty()) {
            details.put("style_id", style);
        }
        Element pPr = firstElementChildByLocalName(paragraph, "pPr");
        if (pPr != null) {
            Element jc = firstElementChildByLocalName(pPr, "jc");
            if (jc != null) {
                details.put("alignment", attributeByLocalName(jc, "val"));
            }
            Element spacing = firstElementChildByLocalName(pPr, "spacing");
            if (spacing != null) {
                details.put("spacing", attributesByLocalName(spacing));
            }
        }
        return details;
    }

    private static List<Element> elementChildren(Element parent) {
        List<Element> children = new ArrayList<>();
        NodeList nodes = parent.getChildNodes();
        for (int index = 0; index < nodes.getLength(); index++) {
            Node node = nodes.item(index);
            if (node instanceof Element) {
                children.add((Element) node);
            }
        }
        return children;
    }

    private static List<Element> elementChildrenByLocalName(Element parent, String wantedLocalName) {
        List<Element> children = new ArrayList<>();
        for (Element child : elementChildren(parent)) {
            if (wantedLocalName.equals(localName(child))) {
                children.add(child);
            }
        }
        return children;
    }

    private static Element firstElementChildByLocalName(Element parent, String wantedLocalName) {
        for (Element child : elementChildren(parent)) {
            if (wantedLocalName.equals(localName(child))) {
                return child;
            }
        }
        return null;
    }

    private static Element firstDescendant(Element parent, String wantedLocalName) {
        if (wantedLocalName.equals(localName(parent))) {
            return parent;
        }
        for (Element child : elementChildren(parent)) {
            Element found = firstDescendant(child, wantedLocalName);
            if (found != null) {
                return found;
            }
        }
        return null;
    }

    private static List<Element> descendants(Element parent, String wantedLocalName) {
        List<Element> found = new ArrayList<>();
        collectDescendants(parent, wantedLocalName, found);
        return found;
    }

    private static void collectDescendants(Element element, String wantedLocalName, List<Element> found) {
        if (wantedLocalName.equals(localName(element))) {
            found.add(element);
        }
        for (Element child : elementChildren(element)) {
            collectDescendants(child, wantedLocalName, found);
        }
    }

    private static String localName(Node node) {
        String local = node.getLocalName();
        if (local != null) {
            return local;
        }
        String name = node.getNodeName();
        int colon = name.indexOf(':');
        return colon >= 0 ? name.substring(colon + 1) : name;
    }

    private static String attributeByLocalName(Element element, String wantedLocalName) {
        NamedNodeMap attributes = element.getAttributes();
        for (int index = 0; index < attributes.getLength(); index++) {
            Node attribute = attributes.item(index);
            if (wantedLocalName.equals(localName(attribute))) {
                return attribute.getNodeValue();
            }
        }
        return "";
    }

    private static Map<String, Object> attributesByLocalName(Element element) {
        Map<String, Object> attributes = orderedMap();
        NamedNodeMap nodeMap = element.getAttributes();
        for (int index = 0; index < nodeMap.getLength(); index++) {
            Node attribute = nodeMap.item(index);
            attributes.put(localName(attribute), attribute.getNodeValue());
        }
        return attributes;
    }

    private static int maxColumnCount(List<Map<String, Object>> cells) {
        int max = 0;
        for (Map<String, Object> cell : cells) {
            Object column = cell.get("column");
            if (column instanceof Number) {
                max = Math.max(max, ((Number) column).intValue());
            }
        }
        return max;
    }

    private static boolean isHeaderFooterPart(String name) {
        String lower = name.toLowerCase(Locale.ROOT);
        return lower.matches("word/(header|footer)\\d+\\.xml");
    }

    private static boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private static Map<String, Object> producer() {
        Map<String, Object> producer = orderedMap();
        producer.put("name", "docfit-docx4j-inspector");
        producer.put("version", "0.1.0");
        producer.put("docx4j_core", "11.5.14");
        return producer;
    }

    private static Map<String, Object> inputHashes(Path input) throws Exception {
        Map<String, Object> hashes = orderedMap();
        if (Files.exists(input)) {
            hashes.put("docx", sha256(Files.readAllBytes(input)));
        }
        return hashes;
    }

    private static String sha256(ZipFile zip, String entryName) throws IOException {
        ZipEntry entry = zip.getEntry(entryName);
        if (entry == null) {
            return "";
        }
        return sha256(zip.getInputStream(entry).readAllBytes());
    }

    private static String sha256(byte[] payload) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(payload);
            StringBuilder builder = new StringBuilder("sha256:");
            for (byte value : bytes) {
                builder.append(String.format("%02x", value));
            }
            return builder.toString();
        } catch (NoSuchAlgorithmException exc) {
            throw new IllegalStateException(exc);
        }
    }

    private static Map<String, Object> orderedMap() {
        return new LinkedHashMap<>();
    }

    private static String toJson(Object value) {
        StringBuilder builder = new StringBuilder();
        writeJson(value, builder);
        return builder.toString();
    }

    @SuppressWarnings("unchecked")
    private static void writeJson(Object value, StringBuilder builder) {
        if (value == null) {
            builder.append("null");
        } else if (value instanceof String) {
            builder.append('"').append(escapeJson((String) value)).append('"');
        } else if (value instanceof Number || value instanceof Boolean) {
            builder.append(value);
        } else if (value instanceof Map<?, ?>) {
            builder.append('{');
            boolean first = true;
            for (Map.Entry<String, Object> entry : ((Map<String, Object>) value).entrySet()) {
                if (!first) {
                    builder.append(',');
                }
                first = false;
                builder.append('"').append(escapeJson(entry.getKey())).append('"').append(':');
                writeJson(entry.getValue(), builder);
            }
            builder.append('}');
        } else if (value instanceof Iterable<?>) {
            builder.append('[');
            boolean first = true;
            for (Object item : (Iterable<?>) value) {
                if (!first) {
                    builder.append(',');
                }
                first = false;
                writeJson(item, builder);
            }
            builder.append(']');
        } else {
            builder.append('"').append(escapeJson(String.valueOf(value))).append('"');
        }
    }

    private static String escapeJson(String value) {
        StringBuilder builder = new StringBuilder();
        for (int index = 0; index < value.length(); index++) {
            char ch = value.charAt(index);
            switch (ch) {
                case '"':
                    builder.append("\\\"");
                    break;
                case '\\':
                    builder.append("\\\\");
                    break;
                case '\b':
                    builder.append("\\b");
                    break;
                case '\f':
                    builder.append("\\f");
                    break;
                case '\n':
                    builder.append("\\n");
                    break;
                case '\r':
                    builder.append("\\r");
                    break;
                case '\t':
                    builder.append("\\t");
                    break;
                default:
                    if (ch < 0x20) {
                        builder.append(String.format("\\u%04x", (int) ch));
                    } else {
                        builder.append(ch);
                    }
            }
        }
        return builder.toString();
    }

    private static final class CliArgs {
        private final Path input;
        private final Path output;

        private CliArgs(Path input, Path output) {
            this.input = input;
            this.output = output;
        }
    }
}
